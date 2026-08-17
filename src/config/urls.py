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

from django_service.views import ShellPreviewView
from inventory.common.views import SpaView, health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    # Story 21.3: the server-rendered shell, mounted under a TEMPORARY prefix.
    #
    # The SPA catch-all below still owns every real page path (/upload, /history, ...)
    # for the whole of Epic 21, so the shell needs somewhere it will not be shadowed —
    # hence `ui/`, which is also added to the catch-all's negative lookahead.
    #
    # Stories 21.5-21.18 claim the real paths one at a time as each page is converted,
    # and Story 21.19 removes the SPA and this prefix along with it.
    path("ui/", ShellPreviewView.as_view(), name="shell-preview"),
    path("api/v1/", include("inventory.users.urls")),
    path("api/v1/", include("inventory.manifests.urls")),
    path("api/v1/", include("inventory.sbom.urls")),
    path("api/v1/", include("inventory.analysis.urls")),
    path("api/v1/", include("inventory.common.urls")),
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

# The SPA catch-all must remain last so it never shadows the routes above. `ui/` joins the
# exclusion list for the server-rendered shell (Story 21.3); it goes away with the SPA in
# Story 21.19.
urlpatterns += [
    re_path(r"^(?!api/|health/|static/|admin/|ui/).*$", SpaView.as_view()),
]
