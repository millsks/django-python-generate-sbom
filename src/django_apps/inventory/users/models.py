"""Organization, membership, and API-key models.

Story 2.1 introduced these alongside the email-based ``User``, building on the minimal
``Org`` created in Story 1.3 (which anchors ``OrgScopedModel``'s FK). ``Org`` is the
tenant root and is NOT org-scoped.

Story 21.2 moved the concrete ``User`` OUT of this module to
``django_service.users`` — the host project owns user identity. These models reach it
through ``settings.AUTH_USER_MODEL`` only; see ``inventory.common.users``.
"""

from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models
from rest_framework_api_key.models import AbstractAPIKey, BaseAPIKeyManager


class Org(models.Model):
    """A tenant boundary; owns all org-scoped resources.

    Exactly one org is the distinguished **ADMIN** org (``is_admin_org=True``).
    Its members are **global admins**: a deliberate, documented cross-org
    superuser tier that is provisioned as a real ADMIN membership into every
    other org (existing and future) and therefore bypasses normal org isolation
    (Story 2.8).
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    is_admin_org = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """Return the org's display name."""
        return self.name


class OrgMembership(models.Model):
    """Links a user to an org with a role (admin or member)."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="memberships")
    # settings.AUTH_USER_MODEL, not "users.User": the app must not name the host's app
    # label. Django treats this as a swappable dependency and resolves it lazily.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="org_memberships")
    role = models.CharField(max_length=10, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("org", "user"),)

    def __str__(self) -> str:
        """Return a readable membership summary."""
        return f"{self.user} in {self.org} ({self.role})"


class OrgApiKeyManager(BaseAPIKeyManager):
    """Manager for OrgApiKey; inherits create_key / get_from_key (AD-8)."""


class OrgApiKey(AbstractAPIKey):
    """An org-scoped API key (SHA-512 hashed by the library; AD-8).

    The library owns key generation, hashing, prefix storage, and lookup via
    ``get_from_key``. We add org scoping and soft revocation (``revoked_at``).
    """

    objects: ClassVar[OrgApiKeyManager] = OrgApiKeyManager()  # type: ignore[assignment]

    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="api_keys")
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta(AbstractAPIKey.Meta):
        verbose_name = "Org API key"
        verbose_name_plural = "Org API keys"
