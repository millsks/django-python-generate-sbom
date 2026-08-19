"""Idempotently seed the deployment's organizations from a list file (Story 22.10).

Modelled on ``seed_superuser``: safe to run on every boot, skips what already exists, and
says why. Compose runs it after ``migrate``; containerless dev picks it up the same way.

Organizations are lines of business, known up front rather than created ad hoc through a form
— a typed name gets you typos, near-duplicates, and slugs nobody chose. The list lives in a
committed file (``INVENTORY_ORGS_FILE``, default ``orgs.yml``) so changes are reviewable.

**Matching is by slug, never by name.** The slug is what `INVENTORY_DEFAULT_ORG_SLUG`, the org
switcher, and API keys reference, so it is the identity; a name is only a label. An org whose
slug already exists is left completely alone — including its name, because silently rewriting
a display name on every boot would make the database follow the file in one direction with no
record of it. A name that differs from the file is *reported* instead, so the operator decides.

Never creates the system ADMIN org: that is migration ``0002``'s job, and an `is_admin_org`
row created here would become a workspace, which Stories 2.12/2.18 exist to prevent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.users.models import Org
from inventory.users.services import ADMIN_ORG_SLUG

logger = structlog.get_logger()


def load_org_specs(path: Path) -> list[dict[str, str]]:
    """Read and validate the org list.

    Raises:
        CommandError: if the file is missing, malformed, or an entry is unusable. A bad list
            stops the boot loudly rather than seeding half of it — a partially-seeded set of
            tenants is worse than none, because jobs would start landing in the wrong place.
    """
    if not path.exists():
        raise CommandError(f"Org list not found: {path}. Set INVENTORY_ORGS_FILE or create the file.")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CommandError(f"{path} is not valid YAML: {exc}") from exc

    if not isinstance(data, dict) or "organizations" not in data:
        raise CommandError(f"{path} must contain a top-level 'organizations:' list.")

    entries = data["organizations"] or []
    if not isinstance(entries, list):
        raise CommandError(f"{path}: 'organizations' must be a list.")

    specs: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise CommandError(f"{path}: entry {index} must be a mapping with 'name' and 'slug'.")
        name, slug = str(entry.get("name", "")).strip(), str(entry.get("slug", "")).strip()
        if not name or not slug:
            raise CommandError(f"{path}: entry {index} needs both 'name' and 'slug'.")
        if slug == ADMIN_ORG_SLUG:
            raise CommandError(
                f"{path}: entry {index} uses the reserved slug '{ADMIN_ORG_SLUG}'. The system ADMIN "
                "org is seeded by migration 0002 and is not a workspace."
            )
        if slug in seen:
            raise CommandError(f"{path}: duplicate slug '{slug}'.")
        seen.add(slug)
        specs.append({"name": name, "slug": slug})
    return specs


class Command(BaseCommand):
    """Create any organizations from the list file that do not already exist."""

    help = "Seed organizations from INVENTORY_ORGS_FILE (idempotent; existing orgs are left untouched)."

    def add_arguments(self, parser: Any) -> None:
        """Register the review flag."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created and exit without writing anything.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Seed the missing orgs, reporting what was created, skipped, or diverged."""
        path = Path(settings.INVENTORY_ORGS_FILE)
        specs = load_org_specs(path)

        existing = {org.slug: org for org in Org.objects.filter(slug__in=[s["slug"] for s in specs])}
        missing = [s for s in specs if s["slug"] not in existing]
        renamed = [s for s in specs if s["slug"] in existing and existing[s["slug"]].name != s["name"]]

        self.stdout.write(f"{path}: {len(specs)} organization(s) listed, {len(missing)} to create.")

        for spec in renamed:
            # Reported, not applied. See the module docstring: the file is the source of the
            # SET of orgs, not a live mirror of their labels.
            self.stdout.write(
                self.style.WARNING(
                    f"  name differs for '{spec['slug']}': database has "
                    f"'{existing[spec['slug']].name}', file says '{spec['name']}' — left unchanged"
                )
            )

        if options["dry_run"]:
            for spec in missing:
                self.stdout.write(f"  would create {spec['slug']} ({spec['name']})")
            self.stdout.write(self.style.WARNING("--dry-run: nothing was written."))
            return

        if not missing:
            self.stdout.write("Nothing to do — every listed organization already exists.")
            logger.info("seed_orgs_skipped", reason="all_exist", listed=len(specs))
            return

        # One transaction: a half-seeded tenant list is the state this is meant to avoid.
        with transaction.atomic():
            for spec in missing:
                Org.objects.create(name=spec["name"], slug=spec["slug"], is_admin_org=False)
                self.stdout.write(f"  created {spec['slug']} ({spec['name']})")

        logger.info("seed_orgs_created", created=len(missing), listed=len(specs))
        self.stdout.write(self.style.SUCCESS(f"Created {len(missing)} organization(s)."))
