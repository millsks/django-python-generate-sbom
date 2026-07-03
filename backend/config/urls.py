# Root URL configuration.
#
# Order matters: the SPA catch-all must come last and must not shadow the API,
# health check, static assets, or the admin site. Story 1.2 adds /health/ and
# Epic 2+ adds the /api/v1/ prefix; the negative-lookahead already excludes them.
from django.contrib import admin
from django.urls import path, re_path

from generate_sbom.common.views import SpaView, health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    re_path(r"^(?!api/|health/|static/|admin/).*$", SpaView.as_view()),
]
