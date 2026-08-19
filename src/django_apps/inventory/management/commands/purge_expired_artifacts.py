"""Purge artifact blobs for jobs past their retention expiry — on request, not on a schedule.

Story 22.6 removed the nightly Beat sweep at the product owner's direction: deleting artifacts
is a deliberate act, taken after looking at what would go. This command is that act.

``artifacts_expire_at`` is still stamped on every job, so expiry is still *tracked*; nothing is
purged until this runs. Job records and their metadata are never deleted (FR-8.1) — only the
downloadable blobs, whose keys are then nulled (AD-6).

    pixi run python manage.py purge_expired_artifacts --dry-run   # review first
    pixi run python manage.py purge_expired_artifacts

Lives at the app root's ``management/commands/`` because Django looks nowhere else — a command
placed inside a sub-package is silently never found (a trap this project has already paid for).
"""

from __future__ import annotations

from typing import Any, cast

import structlog
from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.utils import timezone

from inventory.sbom.models import SBOMJob
from inventory.sbom.services import purge_expired_artifacts

logger = structlog.get_logger()


def expired_jobs_holding_artifacts() -> QuerySet[SBOMJob]:
    """Return the jobs a purge would act on, newest first.

    The selection rule is the one the retired Beat task used, kept identical on purpose:
    past expiry **and** still holding an artifact. Exposed as a function so ``--dry-run`` and
    the tests report on exactly the same set the purge will delete, rather than a second
    query that could drift from it.
    """
    return cast(
        "QuerySet[SBOMJob]",
        SBOMJob.objects.filter(artifacts_expire_at__lte=timezone.now(), result_key__isnull=False)
        .select_related("org")
        .order_by("-artifacts_expire_at"),
    )


class Command(BaseCommand):
    """Delete expired artifact blobs, or report what would be deleted."""

    help = "Purge artifact blobs for jobs past their retention expiry. Job metadata is always kept."

    def add_arguments(self, parser: Any) -> None:
        """Register the review flag."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the jobs that would be purged and exit without deleting anything.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Report the expired jobs, then purge them unless ``--dry-run`` was given."""
        jobs = list(expired_jobs_holding_artifacts())

        if not jobs:
            self.stdout.write("No expired artifacts to purge.")
            return

        # Printed in both modes: even a real run should say what it is about to remove, so the
        # output is a record of what was deleted rather than just a count.
        self.stdout.write(f"{len(jobs)} job(s) past retention expiry and still holding artifacts:")
        for job in jobs:
            reports = job.reports.exclude(artifact_key__isnull=True).count()
            self.stdout.write(
                f"  {job.task_id}  org={job.org.slug}  expired={job.artifacts_expire_at:%Y-%m-%d}  "
                f"sbom=1 reports={reports}"
            )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("--dry-run: nothing was deleted."))
            return

        cleaned = purge_expired_artifacts()
        logger.info("expired_artifacts_purged", jobs_cleaned=cleaned, invoked="management_command")
        self.stdout.write(self.style.SUCCESS(f"Purged artifacts for {cleaned} job(s). Job records were kept."))
