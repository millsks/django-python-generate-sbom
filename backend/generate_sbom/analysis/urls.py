"""URL routes for the analysis app (mounted under /api/v1/)."""

from django.urls import path

from .views import VulnerabilityReportView

urlpatterns = [
    path(
        "sbom/result/<uuid:task_id>/reports/vulnerabilities/",
        VulnerabilityReportView.as_view(),
        name="report-vulnerabilities",
    ),
]
