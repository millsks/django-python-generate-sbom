"""DRF views for analysis report downloads.

These live in the ``analysis`` app (which may import ``sbom``, per the dependency
direction). Blob reports redirect to presigned artifacts — Django never proxies
bytes (AD-11); the dependency-graph JSON is served inline from the report summary
(straight to Cytoscape.js, AD-9). Reports are org-scoped transitively via
``SBOMJob.objects.for_org``.
"""

from __future__ import annotations

from typing import cast

from django.core.files.storage import default_storage
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from generate_sbom.sbom.models import SBOMJob
from generate_sbom.users.auth import get_request_org

from .models import AnalysisReport

_PRESIGN_TTL_SECONDS = 24 * 60 * 60  # 24-hour presigned URL TTL (AD-11)
_NO_ACTIVE_ORG = {"error": "No active org.", "code": "no_active_org"}


def _presigned(key: str) -> str:
    """Presigned URL for ``key`` (S3/MinIO); falls back to a plain URL for FileSystemStorage."""
    try:
        return default_storage.url(key, expire=_PRESIGN_TTL_SECONDS)  # type: ignore[call-arg]
    except TypeError:
        return default_storage.url(key)


def _resolve_job(request: Request, task_id: str) -> tuple[SBOMJob | None, Response | None]:
    """Return (job, None) for the active org, or (None, error_response) on no-org / not-found."""
    org = get_request_org(request)
    if org is None:
        return None, Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
    jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.for_org(org))
    try:
        return jobs.get(task_id=task_id), None
    except SBOMJob.DoesNotExist:
        return None, Response({"error": "Job not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)


def _report_for(job: SBOMJob, report_type: str) -> AnalysisReport | None:
    return AnalysisReport.objects.filter(job=job, report_type=report_type).first()


class _ReportView(APIView):
    """Base: 303-redirect to a presigned analysis-report artifact for the active org."""

    report_type: str

    def get(self, request: Request, task_id: str) -> Response:
        """Return 303 to the presigned report, or 404 for unknown/cross-org/not-ready."""
        job, error = _resolve_job(request, task_id)
        if error is not None:
            return error
        report = _report_for(cast(SBOMJob, job), self.report_type)
        if report is None or report.failed or not report.artifact_key:
            return Response({"error": "Report not available.", "code": "not_ready"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_303_SEE_OTHER, headers={"Location": _presigned(report.artifact_key)})


class VulnerabilityReportView(_ReportView):
    """GET /api/v1/sbom/result/{task_id}/reports/vulnerabilities/ → 303 to vuln.json."""

    report_type = AnalysisReport.ReportType.VULN


class LicenseReportView(_ReportView):
    """GET /api/v1/sbom/result/{task_id}/reports/licenses/ → 303 to licenses.json."""

    report_type = AnalysisReport.ReportType.LICENSE


class GraphSvgDownloadView(_ReportView):
    """GET /api/v1/sbom/result/{task_id}/reports/graph/download/ → 303 to graph.svg."""

    report_type = AnalysisReport.ReportType.GRAPH


class GraphReportView(APIView):
    """GET /api/v1/sbom/result/{task_id}/reports/graph/ → Cytoscape {nodes, edges} JSON (AD-9)."""

    def get(self, request: Request, task_id: str) -> Response:
        """Return the graph JSON inline from the report summary (never PyVis HTML)."""
        job, error = _resolve_job(request, task_id)
        if error is not None:
            return error
        report = _report_for(cast(SBOMJob, job), AnalysisReport.ReportType.GRAPH)
        if report is None or report.failed:
            return Response({"error": "Report not available.", "code": "not_ready"}, status=status.HTTP_404_NOT_FOUND)
        summary = report.summary
        return Response({"nodes": summary.get("nodes", []), "edges": summary.get("edges", [])})
