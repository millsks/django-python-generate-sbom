"""URL routes for the analysis app (mounted under /api/v1/)."""

from django.urls import path

from .views import (
    GraphReportView,
    GraphSvgDownloadView,
    LicenseReportView,
    VulnerabilityReportView,
)

urlpatterns = [
    path(
        "sbom/result/<uuid:task_id>/reports/vulnerabilities/",
        VulnerabilityReportView.as_view(),
        name="report-vulnerabilities",
    ),
    path(
        "sbom/result/<uuid:task_id>/reports/licenses/",
        LicenseReportView.as_view(),
        name="report-licenses",
    ),
    path(
        "sbom/result/<uuid:task_id>/reports/graph/",
        GraphReportView.as_view(),
        name="report-graph",
    ),
    path(
        "sbom/result/<uuid:task_id>/reports/graph/download/",
        GraphSvgDownloadView.as_view(),
        name="report-graph-download",
    ),
]
