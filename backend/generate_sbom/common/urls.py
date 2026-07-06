"""URL routes for shared/public app-level endpoints (mounted under /api/v1/)."""

from django.urls import path

from .config_views import AppConfigView

urlpatterns = [
    path("config/", AppConfigView.as_view(), name="app-config"),
]
