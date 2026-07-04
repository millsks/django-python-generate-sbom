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
