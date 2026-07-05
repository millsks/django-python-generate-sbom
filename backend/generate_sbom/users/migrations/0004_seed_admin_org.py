"""Seed the distinguished ADMIN org (Story 2.8, AC #1)."""

from __future__ import annotations

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

ADMIN_ORG_NAME = "Admin"
ADMIN_ORG_SLUG = "admin"


def seed_admin_org(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Create the ADMIN org row if it is absent (idempotent)."""
    org = apps.get_model("users", "Org")
    org.objects.get_or_create(
        slug=ADMIN_ORG_SLUG,
        defaults={"name": ADMIN_ORG_NAME, "is_admin_org": True},
    )


def unseed_admin_org(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Remove the ADMIN org row on reverse."""
    org = apps.get_model("users", "Org")
    org.objects.filter(slug=ADMIN_ORG_SLUG, is_admin_org=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_org_is_admin_org"),
    ]

    operations = [
        migrations.RunPython(seed_admin_org, unseed_admin_org),
    ]
