"""Read-only queries for the sbom app (AD-3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from django.core.files.storage import default_storage
from django.db.models import QuerySet

from inventory.manifests.models import ManifestUpload
from inventory.users.models import Org

from .document import normalize_components, parse_metadata
from .models import SBOMJob


def get_job(org: Org, task_id: str) -> SBOMJob:
    """Return the org's job by id, or raise SBOMJob.DoesNotExist (→ 404, AD-2)."""
    jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.for_org(org))
    return jobs.get(task_id=task_id)


def get_any_job(task_id: str) -> SBOMJob:
    """Return a job by id regardless of org — for the server-rendered pages (Story 22.16).

    Deliberately **not** org-scoped, and deliberately separate from :func:`get_job`, which
    stays scoped for the API. Since Story 22.16 the organization is provenance on a job rather
    than a browsing boundary: Job Status lists every org's jobs, so following a row through to its
    results must work for all of them.

    This is not a loss of isolation. Anyone could already reach any org's jobs by switching to
    it — `set_active_org_by_slug` accepts every non-ADMIN org since Story 21.24 removed
    membership checks. The switcher made that a two-click detour; this makes it honest. The
    **API** keeps :func:`get_job`, because an API key genuinely pins one tenant (AD-8).
    """
    jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.select_related("manifest", "org"))
    return jobs.get(task_id=task_id)


def get_job_by_task_id(task_id: str) -> SBOMJob:
    """Load a job by task_id for task code (org was established at submission)."""
    jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.select_related("manifest"))
    return jobs.get(task_id=task_id)


# UI status-filter labels → SBOMJob.status values (Story 6.1). Public because the
# server-rendered Job Status FilterSet (Story 21.10) applies the same mapping; two copies of it
# would let the API's filter and the page's filter drift.
STATUS_FILTERS = {
    "In Progress": [SBOMJob.Status.PENDING, SBOMJob.Status.PROGRESS],
    "Completed": [SBOMJob.Status.SUCCESS],
    "Failed": [SBOMJob.Status.FAILED],
}


def get_all_jobs(
    *,
    status_filter: str | None = None,
    format_filter: str | None = None,
) -> QuerySet[SBOMJob]:
    """Return every org's jobs, most-recent-first — the Job Status page's queryset (Story 22.16).

    See :func:`get_any_job` for why the pages are no longer org-scoped. The org travels with
    each row (``select_related("org")``) so the table can show which line of business a job
    was filed against, which is what the removed switcher used to say implicitly.
    """
    jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.select_related("manifest", "org")).order_by("-created_at")
    return _apply_job_filters(jobs, status_filter=status_filter, format_filter=format_filter)


def get_jobs(
    org: Org,
    *,
    status_filter: str | None = None,
    format_filter: str | None = None,
) -> QuerySet[SBOMJob]:
    """Return the org's jobs (most-recent-first), optionally filtered by status/format (AD-2).

    Still org-scoped, and still the API's selector: an API key pins one tenant (AD-8), so a
    programmatic caller must never see another org's jobs. Only the pages went cross-org.
    """
    jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.for_org(org)).select_related("manifest").order_by("-created_at")
    return _apply_job_filters(jobs, status_filter=status_filter, format_filter=format_filter)


def _apply_job_filters(
    jobs: QuerySet[SBOMJob],
    *,
    status_filter: str | None = None,
    format_filter: str | None = None,
) -> QuerySet[SBOMJob]:
    """Apply the status and format filters shared by the org-scoped and cross-org selectors.

    Extracted when Story 22.16 added :func:`get_all_jobs`: two copies of "what does In
    Progress mean" is exactly the drift Story 6.4 was caused by.
    """
    statuses = STATUS_FILTERS.get(status_filter or "")  # "All"/None → no status filter
    if statuses:
        jobs = jobs.filter(status__in=statuses)
    if format_filter:
        # Filter only on a canonical ManifestUpload.Format code (Story 6.4, AD-2). An
        # unknown value — a stale UI or backend/frontend format drift — degrades to an
        # empty result set; it never raises, so a filter selection can't surface an
        # error banner (AC #3).
        if format_filter in ManifestUpload.Format.values:
            jobs = jobs.filter(manifest__detected_format=format_filter)
        else:
            jobs = jobs.none()
    return jobs


@dataclass(frozen=True)
class InlineDocument:
    """A job's generated SBOM, read back for in-page viewing (AD-5)."""

    output_format: str
    metadata: dict[str, Any]
    components: list[dict[str, Any]]
    raw: bytes

    @property
    def size_bytes(self) -> int:
        """Size of the raw document, used to decide inline-vs-download."""
        return len(self.raw)


def read_inline_document(job: SBOMJob) -> InlineDocument | None:
    """Read and parse a job's SBOM for the viewer, or return None if it is unavailable.

    "Unavailable" covers every reason the bytes are not there — never produced, not finished,
    or purged by the retention sweep (Story 7.3) — because the viewer's response is the same
    in all three cases: a notice, not an error. Extracted in Story 21.13 so the DRF endpoint
    and the server-rendered tab read the document the same way.

    Args:
        job: The job whose document to read.

    Returns:
        The parsed document, or None when there is nothing to show.
    """
    if job.status != SBOMJob.Status.SUCCESS or not job.result_key:
        return None
    if not default_storage.exists(job.result_key):
        return None
    with default_storage.open(job.result_key) as handle:
        raw = handle.read()
    return InlineDocument(
        output_format=job.output_format,
        metadata=parse_metadata(raw, job.output_format),
        components=normalize_components(raw, job.output_format),
        raw=raw,
    )
