"""Read-only queries for the sbom app (AD-3)."""

from __future__ import annotations

from typing import cast

from django.db.models import QuerySet

from generate_sbom.users.models import Org

from .models import SBOMJob


def get_job(org: Org, task_id: str) -> SBOMJob:
    """Return the org's job by id, or raise SBOMJob.DoesNotExist (→ 404, AD-2)."""
    jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.for_org(org))
    return jobs.get(task_id=task_id)


def get_job_by_task_id(task_id: str) -> SBOMJob:
    """Load a job by task_id for task code (org was established at submission)."""
    jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.select_related("manifest"))
    return jobs.get(task_id=task_id)


# UI status-filter labels → SBOMJob.status values (Story 6.1).
_STATUS_FILTERS = {
    "In Progress": [SBOMJob.Status.PENDING, SBOMJob.Status.PROGRESS],
    "Completed": [SBOMJob.Status.SUCCESS],
    "Failed": [SBOMJob.Status.FAILED],
}


def get_jobs(
    org: Org,
    *,
    status_filter: str | None = None,
    format_filter: str | None = None,
) -> QuerySet[SBOMJob]:
    """Return the org's jobs (most-recent-first), optionally filtered by status/format (AD-2)."""
    jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.for_org(org)).select_related("manifest").order_by("-created_at")
    statuses = _STATUS_FILTERS.get(status_filter or "")  # "All"/None → no status filter
    if statuses:
        jobs = jobs.filter(status__in=statuses)
    if format_filter:
        jobs = jobs.filter(manifest__detected_format=format_filter)
    return jobs
