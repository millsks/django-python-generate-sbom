"""DRF authentication + permission for the Api-Key path (AD-8).

The web-UI path uses session auth (Story 2.2); this adds the programmatic path.
``OrgApiKeyAuthentication`` resolves ``Authorization: Api-Key <key>`` to an
``OrgApiKey`` via the library (SHA-512, no hand-rolled crypto), rejects revoked
keys, updates ``last_used_at``, and exposes ``request.auth.org``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .models import OrgApiKey

if TYPE_CHECKING:
    from rest_framework.views import APIView

_KEYWORD = "Api-Key"
_INVALID_KEY = "Invalid or revoked API key."


class OrgApiKeyAuthentication(BaseAuthentication):
    """Authenticate ``Authorization: Api-Key <key>`` requests to an OrgApiKey."""

    def authenticate(self, request: Request) -> tuple[AnonymousUser, OrgApiKey] | None:
        """Return (AnonymousUser, OrgApiKey) or None to defer to session auth."""
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{_KEYWORD} "):
            return None
        raw_key = header[len(_KEYWORD) + 1 :].strip()
        try:
            api_key = cast(OrgApiKey, OrgApiKey.objects.get_from_key(raw_key))
        except OrgApiKey.DoesNotExist:
            raise AuthenticationFailed({"error": _INVALID_KEY, "code": "invalid_api_key"}) from None
        if api_key.revoked_at is not None:
            raise AuthenticationFailed({"error": _INVALID_KEY, "code": "invalid_api_key"})
        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=["last_used_at"])
        return AnonymousUser(), api_key

    def authenticate_header(self, request: Request) -> str:
        """Return the WWW-Authenticate header value so failures render as 401."""
        return _KEYWORD


class HasSessionOrApiKey(BasePermission):
    """Allow either a session-authenticated user or a valid OrgApiKey."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Pass when the caller has a session user or a resolved API key."""
        if request.user and request.user.is_authenticated:
            return True
        return isinstance(request.auth, OrgApiKey)
