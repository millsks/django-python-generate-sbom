"""URL routes for the analysis app (mounted under /api/v1/)."""

from django.urls import path

from .views import LicenseReportView, VulnerabilityReportView

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
]
