"""Idempotently seed the initial superuser (global admin) from environment variables.

When ``DJANGO_SUPERUSER_EMAIL`` and ``DJANGO_SUPERUSER_PASSWORD`` are set and no user
with that email exists, create a superuser — which the ``create_superuser`` hook seeds
into the ADMIN org, making them a global admin (Story 2.8). Safe to run on every boot
(Story 2.13): it skips cleanly when the vars are unset or the user already exists.
"""

from __future__ import annotations

import os
from typing import Any

import structlog
from django.core.management.base import BaseCommand

from ...models import User

logger = structlog.get_logger()


class Command(BaseCommand):
    """Seed the initial superuser (global admin) from environment variables."""

    help = "Seed the initial superuser from DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD (idempotent)."

    def handle(self, *args: Any, **options: Any) -> None:
        """Create the env-configured superuser if set and not already present (never logs the password)."""
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not email or not password:
            logger.info("seed_superuser_skipped", reason="env_not_set")
            return
        if User.objects.filter(email__iexact=email).exists():
            logger.info("seed_superuser_skipped", reason="already_exists", email=email)
            return
        User.objects.create_superuser(email=email, password=password)
        logger.info("seed_superuser_created", email=email)
