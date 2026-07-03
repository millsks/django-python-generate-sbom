"""Views shared across the project."""

from pathlib import Path

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.views import View


class SpaView(View):
    """Serve the built React SPA's ``index.html`` for all non-API routes (AD-5).

    React Router handles client-side routing in the browser, so every non-API,
    non-static path returns the same SPA entrypoint.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Return the SPA entrypoint, or 404 when the frontend has not been built."""
        index = Path(settings.SPA_INDEX_FILE)
        if index.exists():
            return HttpResponse(index.read_text(encoding="utf-8"))
        return HttpResponseNotFound("SPA not built. Run: pixi run fe-build")
