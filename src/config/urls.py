# Root URL configuration.
#
# Story 21.19 retired the React SPA, and with it the catch-all that used to sit at the
# bottom of this file serving `index.html` for every unmatched path. Nothing is a
# fallback now: an unmatched path 404s, which is the point — a mistyped URL used to
# answer 200 with the landing page, hiding broken links.
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import URLPattern, include, path

from django_service.views import LandingPageView, ShellPreviewView
from inventory.common.views import health

urlpatterns = [
    path("", LandingPageView.as_view(), name="ui-home"),
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    # The shell preview from Story 21.3, kept as a rendering harness for the base
    # template. The `ui/` prefix existed to escape the SPA catch-all; with the catch-all
    # gone it is now just this page's path.
    path("ui/", ShellPreviewView.as_view(), name="shell-preview"),
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


def media_urlpatterns() -> list[URLPattern]:
    """Serve ``MEDIA_ROOT`` from the development server, and only there (Story 22.28).

    Containerless local development stores artifacts with ``FileSystemStorage``, whose
    ``url()`` returns ``/media/…``. The SBOM download redirects to exactly that (AD-11), so
    without this route the dev server had no pattern for its own storage URLs and every
    download 404'd. In containers the same code works untouched, because MinIO serves the blob
    rather than Django — which is why this only ever broke on the path this epic protects.

    Guarded on ``DEBUG`` rather than on the storage backend. Django serving user uploads in
    production would bypass the storage backend entirely and hand out every stored manifest
    over an unauthenticated path — and this application has no authentication (Story 21.24), so
    the absence of the route is the only thing standing between the two.

    A function rather than an inline ``if`` so the rule can be tested without reimporting the
    URLconf: module-level ``DEBUG`` branches are evaluated once at import and are effectively
    untestable afterwards.
    """
    if not settings.DEBUG:
        return []
    return static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


urlpatterns += media_urlpatterns()
