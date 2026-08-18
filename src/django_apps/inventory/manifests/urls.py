"""URL routes for the manifests app (mounted under /api/v1/)."""

from django.urls import path

from .views import ManifestUploadView

urlpatterns = [
    path("manifests/upload/", ManifestUploadView.as_view(), name="manifest-upload"),
]
