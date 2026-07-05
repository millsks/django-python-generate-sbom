# Root URL configuration.
#
# Order matters: the SPA catch-all must come last and must not shadow the API,
# health check, static assets, or the admin site. Story 1.2 adds /health/ and
# Epic 2+ adds the /api/v1/ prefix; the negative-lookahead already excludes them.
# Story 11.9 adds the OpenAPI schema + Swagger UI/ReDoc under /api/ (gated by
# API_DOCS_ENABLED), which the catch-all's `api/` exclusion already keeps clear.
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from generate_sbom.common.views import SpaView, health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("generate_sbom.users.urls")),
    path("api/v1/", include("generate_sbom.manifests.urls")),
    path("api/v1/", include("generate_sbom.sbom.urls")),
    path("api/v1/", include("generate_sbom.analysis.urls")),
]

# Interactive API docs (Story 11.9) — served only when enabled for the environment.
if settings.API_DOCS_ENABLED:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]

# The SPA catch-all must remain last so it never shadows the routes above.
urlpatterns += [
    re_path(r"^(?!api/|health/|static/|admin/).*$", SpaView.as_view()),
]
