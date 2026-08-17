"""Seed the distinguished ADMIN org (Story 2.8, AC #1).

Ported unchanged in behaviour from the dissolved ``users.0004_seed_admin_org`` when
Story 21.2 collapsed the four app labels into ``inventory``. The only edit is the
``get_model`` app label: ``("users", "Org")`` -> ``("inventory", "Org")``. Kept as a
separate ``0002`` rather than folded into ``0001_initial`` so the data step stays legible
and independently reversible.
"""

from __future__ import annotations

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

ADMIN_ORG_NAME = "Admin"
ADMIN_ORG_SLUG = "admin"


def seed_admin_org(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Create the ADMIN org row if it is absent (idempotent)."""
    org = apps.get_model("inventory", "Org")
    org.objects.get_or_create(
        slug=ADMIN_ORG_SLUG,
        defaults={"name": ADMIN_ORG_NAME, "is_admin_org": True},
    )


def unseed_admin_org(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Remove the ADMIN org row on reverse."""
    org = apps.get_model("inventory", "Org")
    org.objects.filter(slug=ADMIN_ORG_SLUG, is_admin_org=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_admin_org, unseed_admin_org),
    ]
