"""Public runtime config for the SPA (Story 11.20)."""

from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class AppConfigView(APIView):
    """Public runtime config for the SPA (GET /api/v1/config/).

    Surfaces deploy-time feature flags the SPA needs before — and without — auth.
    ``api_docs_enabled`` mirrors ``settings.API_DOCS_ENABLED``, the same flag that
    gates the ``/api/docs/`` Swagger UI, so the header link and the endpoint enable
    together and the link can never point at a disabled (404) endpoint. Public and
    read-only: no auth or CSRF needed for a feature flag. The payload is an object so
    future flags can be added without a breaking change.
    """

    authentication_classes = []  # noqa: RUF012
    permission_classes = [AllowAny]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        """Return the SPA's public runtime config."""
        return Response({"api_docs_enabled": settings.API_DOCS_ENABLED})
