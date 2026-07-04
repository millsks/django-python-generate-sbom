"""DRF views for the sbom app.

The generate view lives here (not in manifests) because it creates ``SBOMJob``
and imports the manifest upload service — the ``sbom → manifests`` dependency
direction (AD-1) requires ``sbom`` to be the importer. AD-7's invariant (atomic
gate-then-create) is preserved by the transaction, independent of file location.
"""

from __future__ import annotations

from typing import cast

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from generate_sbom.manifests.detection import ManifestParseError, UnsupportedFormatError
from generate_sbom.manifests.services import upload_manifest
from generate_sbom.tasks.sbom_pipeline import run_sbom_pipeline
from generate_sbom.users.auth import get_request_org

from .models import SBOMJob
from .selectors import get_job, get_jobs
from .serializers import GenerateJobSerializer, JobListSerializer
from .services import OUTPUT_FORMAT_MAP, create_job, estimate_seconds, mark_stale_job_timed_out

_NO_ACTIVE_ORG = {"error": "No active org.", "code": "no_active_org"}
_ACTIVE_STATUSES = [SBOMJob.Status.PENDING, SBOMJob.Status.PROGRESS]
_PRESIGN_TTL_SECONDS = 24 * 60 * 60  # 24-hour presigned URL TTL (AD-11)


class GenerateJobView(APIView):
    """Submit a manifest for SBOM generation (POST /api/v1/sbom/generate/)."""

    parser_classes = [MultiPartParser, FormParser]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        """Gate on concurrency, create the job, and dispatch the pipeline (AD-7/10)."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)

        jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.for_org(org))
        active = jobs.filter(status__in=_ACTIVE_STATUSES).count()
        if active >= settings.SBOM_MAX_CONCURRENT_JOBS_PER_ORG:
            return Response(
                {"error": "Concurrent job limit reached", "code": "rate_limited"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "60"},
            )

        serializer = GenerateJobSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"error": str(first_error), "code": "validation_error"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        user = request.user if request.user.is_authenticated else None
        size = getattr(data["file"], "size", 0)

        with transaction.atomic():
            try:
                upload = upload_manifest(
                    org,
                    user,
                    file_obj=data["file"],
                    application_id=data["application_id"],
                    component_name=data["component_name"],
                    repository_url=data["repository_url"],
                    source_branch=data["source_branch"],
                )
            except UnsupportedFormatError as exc:
                return Response(
                    {"error": str(exc), "code": "unsupported_format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except ManifestParseError as exc:
                return Response(
                    {"error": str(exc), "code": "parse_error"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            job = create_job(org, upload, user, OUTPUT_FORMAT_MAP[data["output_format"]])
            run_sbom_pipeline.delay_on_commit(str(job.task_id))

        return Response(
            {
                "task_id": str(job.task_id),
                "status": job.status,
                "status_url": f"/api/v1/sbom/status/{job.task_id}/",
                "estimated_seconds": estimate_seconds(upload.detected_format, size),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class JobsPagination(PageNumberPagination):
    """25 jobs per page; up to 100 via ?page_size= (solution-design §5.3)."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class JobsListView(ListAPIView[SBOMJob]):
    """List the active org's jobs, most-recent-first (GET /api/v1/sbom/jobs/)."""

    serializer_class = JobListSerializer
    pagination_class = JobsPagination

    def get_queryset(self) -> QuerySet[SBOMJob]:
        """Return the org's jobs with the requested status/format filters (AD-2)."""
        org = get_request_org(self.request)
        if org is None:
            return cast("QuerySet[SBOMJob]", SBOMJob.objects.none())
        return get_jobs(
            org,
            status_filter=self.request.query_params.get("status"),
            format_filter=self.request.query_params.get("format"),
        )


class StatusJobView(APIView):
    """Poll a job's status (GET /api/v1/sbom/status/{task_id}/)."""

    def get(self, request: Request, task_id: str) -> Response:
        """Return the job status shape, or 404 for cross-org / unknown (AD-2)."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
        try:
            job = get_job(org, task_id)
        except SBOMJob.DoesNotExist:
            return Response(
                {"error": "Job not found.", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        # A hard timeout force-kills the worker, so the poll detects the stale job (FR-4.6).
        if mark_stale_job_timed_out(job):
            job = get_job(org, task_id)
        result_url = f"/api/v1/sbom/result/{job.task_id}/" if job.status == SBOMJob.Status.SUCCESS else None
        return Response(
            {
                "task_id": str(job.task_id),
                "status": job.status,
                "progress": job.progress,
                "current_phase": job.current_step,
                "failure_reason": job.failure_reason,
                "result_url": result_url,
                "output_format": job.output_format,
                "summary_stats": job.summary_stats,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
        )


class ResultJobView(APIView):
    """Redirect to a presigned SBOM download (GET /api/v1/sbom/result/{task_id}/).

    Django never streams artifact bytes — it issues a 303 to a presigned
    S3/MinIO URL (AD-11). The code path is identical for MinIO (dev) and S3 (prod).
    """

    def get(self, request: Request, task_id: str) -> Response:
        """Return 303 to a presigned artifact URL, or 404 for unknown/cross-org/not-ready."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
        try:
            job = get_job(org, task_id)
        except SBOMJob.DoesNotExist:
            return Response({"error": "Job not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)
        if job.status != SBOMJob.Status.SUCCESS or not job.result_key:
            return Response(
                {"error": "Result not ready.", "code": "not_ready"},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            url = default_storage.url(job.result_key, expire=_PRESIGN_TTL_SECONDS)  # type: ignore[call-arg]
        except TypeError:
            # FileSystemStorage (dev/tests) has no presigning; url() takes only the name.
            url = default_storage.url(job.result_key)
        return Response(status=status.HTTP_303_SEE_OTHER, headers={"Location": url})
