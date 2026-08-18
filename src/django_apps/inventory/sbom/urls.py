"""URL routes for the sbom app (mounted under /api/v1/)."""

from django.urls import path

from .views import (
    BulkDeleteArtifactsView,
    GenerateJobView,
    JobArtifactsView,
    JobsListView,
    ResultJobView,
    SbomDocumentView,
    StatusJobView,
)

urlpatterns = [
    path("sbom/generate/", GenerateJobView.as_view(), name="sbom-generate"),
    path("sbom/jobs/", JobsListView.as_view(), name="sbom-jobs"),
    path("sbom/jobs/artifacts/bulk-delete/", BulkDeleteArtifactsView.as_view(), name="sbom-artifacts-bulk-delete"),
    path("sbom/jobs/<uuid:task_id>/artifacts/", JobArtifactsView.as_view(), name="sbom-job-artifacts"),
    path("sbom/status/<uuid:task_id>/", StatusJobView.as_view(), name="sbom-status"),
    path("sbom/result/<uuid:task_id>/", ResultJobView.as_view(), name="sbom-result"),
    path("sbom/document/<uuid:task_id>/", SbomDocumentView.as_view(), name="sbom-document"),
]
