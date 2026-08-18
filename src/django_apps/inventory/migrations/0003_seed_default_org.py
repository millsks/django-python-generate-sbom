"""Seed the default org that anonymous callers act as (Story 21.24, AC #4).

Story 21.24 removed the app's own authentication: every page and endpoint is now reachable
without logging in, and identity becomes the host platform's responsibility (Epics 17-18).
An anonymous caller still has to act as *some* org, because AD-2 makes the org the tenancy
boundary and every service takes one as its first positional argument.

Modelled on ``0002_seed_admin_org``: idempotent ``get_or_create``, reversible. Kept a
separate data migration for the same reason — the step stays legible and can be reversed on
its own.

``is_admin_org=False`` is load-bearing. The ADMIN org is a meta org, not a workspace
(Stories 2.12/2.18), and pointing the anonymous default at it would resurrect exactly the
bug those stories fixed.
"""

from __future__ import annotations

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

DEFAULT_ORG_NAME = "Enterprise Wells Fargo Technology"
DEFAULT_ORG_SLUG = "enterprise-wells-fargo-technology"


def seed_default_org(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Create the default org row if it is absent (idempotent)."""
    org = apps.get_model("inventory", "Org")
    org.objects.get_or_create(
        slug=DEFAULT_ORG_SLUG,
        defaults={"name": DEFAULT_ORG_NAME, "is_admin_org": False},
    )


def unseed_default_org(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Remove the default org row on reverse."""
    org = apps.get_model("inventory", "Org")
    org.objects.filter(slug=DEFAULT_ORG_SLUG, is_admin_org=False).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_seed_admin_org"),
    ]

    operations = [
        migrations.RunPython(seed_default_org, unseed_default_org),
    ]
