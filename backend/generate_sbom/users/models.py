"""User and organization models.

Story 2.1 introduces the email-based custom ``User`` and the ``OrgMembership``
link, and builds on the minimal ``Org`` created in Story 1.3 (which anchors
``OrgScopedModel``'s FK). ``Org`` is the tenant root and is NOT org-scoped.
"""

from __future__ import annotations

from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from rest_framework_api_key.models import AbstractAPIKey, BaseAPIKeyManager


class UserManager(DjangoUserManager["User"]):
    """Manager for the email-based User model (no username)."""

    def create_user(  # type: ignore[override]
        self, email: str, password: str | None = None, **extra_fields: object
    ) -> User:
        """Create and save a user identified by email."""
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(  # type: ignore[override]
        self, email: str, password: str | None = None, **extra_fields: object
    ) -> User:
        """Create and save a superuser identified by email."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """A person with an account; email is the unique login identifier."""

    username = None  # type: ignore[assignment]
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects = UserManager()  # type: ignore[misc]

    def __str__(self) -> str:
        """Return the user's email."""
        return self.email


class Org(models.Model):
    """A tenant boundary; owns all org-scoped resources."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
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
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="org_memberships")
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
