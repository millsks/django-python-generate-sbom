# Root URL configuration.
#
# Story 21.19 retired the React SPA, and with it the catch-all that used to sit at the
# bottom of this file serving `index.html` for every unmatched path. Nothing is a
# fallback now: an unmatched path 404s, which is the point — a mistyped URL used to
# answer 200 with the landing page, hiding broken links.
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from django_service.views import LandingPageView, OrgSwitchView, ShellPreviewView
from inventory.common.views import health

urlpatterns = [
    path("", LandingPageView.as_view(), name="ui-home"),
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    # The shell preview from Story 21.3, kept as a rendering harness for the base
    # template. The `ui/` prefix existed to escape the SPA catch-all; with the catch-all
    # gone it is now just this page's path.
    path("ui/", ShellPreviewView.as_view(), name="shell-preview"),
    # The org switcher form posts here (Story 21.4).
    #
    # The name is `ui-org-switch`, NOT `org-switch`: inventory/users/urls.py already
    # registers `org-switch` for the DRF endpoint, and Django resolves a duplicate name to
    # whichever pattern is registered LAST — which silently pointed the HTML form at the
    # JSON API. tests/unit/test_org_switcher.py pins the resolved action.
    path("ui/orgs/switch/", OrgSwitchView.as_view(), name="ui-org-switch"),
    # The app's server-rendered pages (Stories 21.5-21.18), at their real paths.
    path("", include("inventory.urls_pages")),
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
