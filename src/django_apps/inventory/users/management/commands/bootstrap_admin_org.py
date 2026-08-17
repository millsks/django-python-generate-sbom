"""Idempotently ensure the ADMIN org exists and seed superusers as global admins.

Covers already-existing superusers created before the ``create_superuser``
hook was in place (Story 2.8, Task 2).
"""

from __future__ import annotations

from typing import Any

import structlog
from django.core.management.base import BaseCommand

from ... import services
from ...models import Org, User

logger = structlog.get_logger()


class Command(BaseCommand):
    """Ensure the ADMIN org exists and back-fill all superusers as global admins."""

    help = "Ensure the ADMIN org exists and seed all superusers as global admins."

    def handle(self, *args: Any, **options: Any) -> None:
        """Create the ADMIN org if missing, then grant every superuser global admin."""
        Org.objects.get_or_create(
            slug=services.ADMIN_ORG_SLUG,
            defaults={"name": services.ADMIN_ORG_NAME, "is_admin_org": True},
        )
        for user in User.objects.filter(is_superuser=True):
            services.grant_global_admin(user)
        logger.info("bootstrap_admin_org_complete")
