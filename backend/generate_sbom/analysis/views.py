"""DRF views for analysis reports.

These live in the ``analysis`` app (which may import ``sbom``, per the dependency
direction). Report JSON (vuln/license/version) is served inline for the SPA tabs.
Genuine file downloads redirect to a presigned artifact (Django never proxies
download bytes, AD-11). Reports are org-scoped transitively via
``SBOMJob.objects.for_org``.
"""

from __future__ import annotations

import json
from typing import Any, cast

from django.core.files.storage import default_storage
from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from generate_sbom.sbom.models import SBOMJob
from generate_sbom.users.auth import get_request_org
from generate_sbom.users.serializers import ErrorResponseSerializer

from .models import AnalysisReport

_NO_ACTIVE_ORG = {"error": "No active org.", "code": "no_active_org"}


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


def _unavailable(report: AnalysisReport | None) -> Response | None:
    """Return a 404 for a missing or failed report (conveying the reason), else None."""
    if report is None:
        return Response({"error": "Report not available.", "code": "not_ready"}, status=status.HTTP_404_NOT_FOUND)
    if report.failed:
        return Response(
            {"error": "Report generation failed.", "code": "report_failed", "failure_reason": report.failure_reason},
            status=status.HTTP_404_NOT_FOUND,
        )
    return None


class _JsonReportView(APIView):
    """Base: serve a report's JSON artifact inline (200) for the SPA tabs."""

    report_type: str

    @extend_schema(responses={200: OpenApiTypes.OBJECT, 404: ErrorResponseSerializer})
    def get(self, request: Request, task_id: str) -> Response:
        """Return the report JSON, or 404 for unknown/cross-org/not-ready/failed."""
        job, error = _resolve_job(request, task_id)
        if error is not None:
            return error
        report = _report_for(cast(SBOMJob, job), self.report_type)
        unavailable = _unavailable(report)
        if unavailable is not None:
            return unavailable
        report = cast(AnalysisReport, report)
        if not report.artifact_key:
            return Response({"error": "Report not available.", "code": "not_ready"}, status=status.HTTP_404_NOT_FOUND)
        with default_storage.open(report.artifact_key) as handle:
            data: Any = json.loads(handle.read())
        return Response(data)


class VulnerabilityReportView(_JsonReportView):
    """GET /api/v1/sbom/result/{task_id}/reports/vulnerabilities/ → vulnerability JSON."""

    report_type = AnalysisReport.ReportType.VULN


class LicenseReportView(_JsonReportView):
    """GET /api/v1/sbom/result/{task_id}/reports/licenses/ → license JSON."""

    report_type = AnalysisReport.ReportType.LICENSE


class VersionReportView(_JsonReportView):
    """GET /api/v1/sbom/result/{task_id}/reports/versions/ → version currency JSON."""

    report_type = AnalysisReport.ReportType.VERSION
