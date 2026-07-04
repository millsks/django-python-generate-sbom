"""DRF views for analysis report downloads.

These live in the ``analysis`` app (which may import ``sbom``, per the dependency
direction) and redirect to presigned report artifacts — Django never proxies bytes
(AD-11). Reports are org-scoped transitively via ``SBOMJob.objects.for_org``.
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


class _ReportView(APIView):
    """Base: 303-redirect to a presigned analysis-report artifact for the active org."""

    report_type: str

    def get(self, request: Request, task_id: str) -> Response:
        """Return 303 to the presigned report, or 404 for unknown/cross-org/not-ready."""
        org = get_request_org(request)
        if org is None:
            return Response(_NO_ACTIVE_ORG, status=status.HTTP_404_NOT_FOUND)
        jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.for_org(org))
        try:
            job = jobs.get(task_id=task_id)
        except SBOMJob.DoesNotExist:
            return Response({"error": "Job not found.", "code": "not_found"}, status=status.HTTP_404_NOT_FOUND)
        report = AnalysisReport.objects.filter(job=job, report_type=self.report_type).first()
        if report is None or report.failed or not report.artifact_key:
            return Response({"error": "Report not available.", "code": "not_ready"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_303_SEE_OTHER, headers={"Location": _presigned(report.artifact_key)})


class VulnerabilityReportView(_ReportView):
    """GET /api/v1/sbom/result/{task_id}/reports/vulnerabilities/ → 303 to vuln.json."""

    report_type = AnalysisReport.ReportType.VULN


class LicenseReportView(_ReportView):
    """GET /api/v1/sbom/result/{task_id}/reports/licenses/ → 303 to licenses.json."""

    report_type = AnalysisReport.ReportType.LICENSE
