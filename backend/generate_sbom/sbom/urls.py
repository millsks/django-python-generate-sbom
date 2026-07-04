"""URL routes for the sbom app (mounted under /api/v1/)."""

from django.urls import path

from .views import GenerateJobView, ResultJobView, StatusJobView

urlpatterns = [
    path("sbom/generate/", GenerateJobView.as_view(), name="sbom-generate"),
    path("sbom/status/<uuid:task_id>/", StatusJobView.as_view(), name="sbom-status"),
    path("sbom/result/<uuid:task_id>/", ResultJobView.as_view(), name="sbom-result"),
]
