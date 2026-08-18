"""The concrete, email-login ``User`` — owned by the HOST project, not the app.

Story 2.1 introduced this model inside the old ``generate_sbom.users`` app. Story 21.2
moved it here, keeping the ``users`` app label so ``AUTH_USER_MODEL`` still reads
``"users.User"``. Nothing under ``src/django_apps/inventory/`` may import these classes;
the app reaches user identity through ``settings.AUTH_USER_MODEL`` (model FKs) and
``inventory.common.users`` (runtime + type annotations).
"""

from __future__ import annotations

from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


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
        """Create and save a superuser and make them a global admin.

        After the user is created, ``grant_global_admin`` seeds them into the ADMIN
        org (Story 2.8). It returns early if the ADMIN org does not yet exist (e.g.
        migrations have not run), so this is safe at any point in the migration
        lifecycle.

        The import is deferred, and it points at the app on purpose. This is the HOST
        depending on the app, which is the allowed direction — the app never depends on
        the host. Keeping it lazy also avoids importing app models while the registry is
        still populating.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        user = self.create_user(email, password, **extra_fields)
        from inventory.users.services import grant_global_admin

        grant_global_admin(user)
        return user


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
