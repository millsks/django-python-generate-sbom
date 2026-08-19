"""django-tables2 tables for the server-rendered SBOM pages (Story 21.10)."""

from __future__ import annotations

from typing import Any

import django_tables2 as tables
from django.template.defaultfilters import capfirst
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import SafeString

from .models import SBOMJob
from .services import TERMINAL_STATUSES

#: How often a running job refreshes itself. Matches POLL_MS = 5000 in useJobStatus.ts.
POLL_INTERVAL = "5s"


def poll_attrs(job: SBOMJob) -> dict[str, str]:
    """Return the htmx attributes that make a row poll — or nothing if it is finished.

    The single trigger convention (Story 21.11). The SPA deliberately centralised polling in
    one hook "so there are no per-component polling loops"; the server-side equivalent is that
    this function is the only place a poll trigger is produced.

    A terminal job gets **no attributes at all**, so it issues no requests — and because the
    refreshed markup is produced by this same function, a job that finishes mid-poll comes
    back without a trigger and polling self-terminates. That is more robust than asking the
    client to cancel itself.
    """
    if job.status in TERMINAL_STATUSES:
        return {}
    return {
        "hx-get": reverse("ui-job-row", kwargs={"task_id": job.task_id}),
        "hx-trigger": f"every {POLL_INTERVAL}",
        "hx-swap": "outerHTML",
    }


#: SBOMJob.status → (label, Bootstrap contextual class), carried over from
#: JobStatusBadge.tsx so the wording a user sees does not change with the rendering stack.
STATUS_BADGES = {
    SBOMJob.Status.PENDING: ("In Progress", "text-bg-info"),
    SBOMJob.Status.PROGRESS: ("In Progress", "text-bg-info"),
    SBOMJob.Status.SUCCESS: ("Completed", "text-bg-success"),
    SBOMJob.Status.FAILED: ("Failed", "text-bg-danger"),
}


def format_duration(seconds: float | None) -> str:
    """Format a duration the way ``duration.ts`` did (Story 6.3).

    Ported rather than reinvented so the Job Status page reads identically before and after the
    conversion: an em dash when unknown, then ms / s / m+s / h+m.

    Args:
        seconds: Elapsed seconds, or None when the job has not finished.

    Returns:
        A short human-readable duration.
    """
    if seconds is None or seconds < 0:
        return "—"
    if seconds < 1:
        return f"{round(seconds * 1000)}ms"
    if seconds < 60:
        return f"{round(seconds)}s"
    if seconds < 3600:
        minutes, remainder = divmod(seconds, 60)
        return f"{int(minutes)}m {round(remainder)}s"
    hours, remainder = divmod(seconds, 3600)
    return f"{int(hours)}h {int(remainder // 60):02d}m"


class JobTable(tables.Table):
    """The org's SBOM jobs — the columns ``HistoryPage.tsx`` rendered, in the same order."""

    select = tables.CheckBoxColumn(
        accessor="task_id",
        orderable=False,
        # Selection is per page, matching the SPA's `toggleAll`, which only ever covered the
        # rows currently fetched. The confirmation copy says so explicitly.
        attrs={"th__input": {"id": "select-all", "aria-label": "Select all rows on this page"}},
        verbose_name="",
    )
    # Story 22.16: with the org switcher gone, Job Status lists every org and this column is
    # what says which one a job was filed against. It leads the data columns because that is
    # the question the switcher used to answer before you read anything else.
    org = tables.Column(accessor="org__name", verbose_name="Organization", orderable=True)
    created_at = tables.DateTimeColumn(verbose_name="Submitted", format="Y-m-d H:i")
    manifest = tables.Column(accessor="manifest__original_filename", verbose_name="Manifest", orderable=False)
    detected_format = tables.Column(accessor="manifest__detected_format", verbose_name="Format", orderable=False)
    output_format = tables.Column(verbose_name="Output", orderable=False)
    status = tables.Column(verbose_name="Status")
    elapsed = tables.Column(empty_values=(), verbose_name="Elapsed", orderable=False)
    results = tables.Column(empty_values=(), verbose_name="Results", orderable=False)

    class Meta:
        # django-tables2 Meta options, not mutable dataclass defaults — same exemption the
        # project already applies to Django model Meta classes.
        model = SBOMJob
        fields = ("select", "org", "created_at", "manifest", "detected_format", "output_format", "status", "elapsed")
        # Newest-first is the queryset's ordering; stated here too so a user clearing the sort
        # returns to it rather than to an undefined order.
        order_by = "-created_at"
        attrs = {"class": "table align-middle"}  # noqa: RUF012  # tables2 Meta option, not a dataclass default
        empty_text = "No jobs yet."
        # Only non-terminal rows carry a trigger, which is the single biggest load
        # difference between this and a naive implementation: a page of finished jobs
        # issues zero requests.
        row_attrs = {  # noqa: RUF012  # tables2 Meta option
            "id": lambda record: f"job-row-{record.task_id}",
            **{
                name: (lambda attr: lambda record: poll_attrs(record).get(attr, ""))(name)
                for name in ("hx-get", "hx-trigger", "hx-swap")
            },
        }

    def render_detected_format(self, value: str, record: SBOMJob) -> str:
        """Show the manifest format's human label rather than its code."""
        return record.manifest.get_detected_format_display()

    def render_status(self, record: SBOMJob) -> SafeString:
        """Render the status badge, including the purged-artifact indicator (Story 7.3).

        Reads ``record.status`` rather than the column's ``value``: because the field has
        ``choices``, django-tables2 hands the renderer the *display* label ("Success"), not
        the stored code ("SUCCESS"), and the badge map is keyed by the code.
        """
        label, css = STATUS_BADGES.get(SBOMJob.Status(record.status), (record.status, "text-bg-secondary"))
        badge = format_html('<span class="badge {}">{}</span>', css, label)
        if record.status == SBOMJob.Status.PROGRESS or record.status == SBOMJob.Status.PENDING:
            # Story 6.2: an in-progress row shows its phase and percentage, not just a badge.
            return format_html(
                '{}<div class="small text-body-secondary mt-1">{}</div>'
                '<div class="progress mt-1" style="height:4px;" role="progressbar" '
                'aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">'
                '<div class="progress-bar" style="width:{}%"></div></div>',
                badge,
                capfirst(record.current_step or "Queued"),
                record.progress,
                record.progress,
            )
        if record.status == SBOMJob.Status.FAILED and record.failure_reason:
            return format_html('{} <span class="small text-danger">{}</span>', badge, record.failure_reason)
        if _artifacts_purged(record):
            # The metadata survives forever (FR-8.1); only the blobs are gone, and the row
            # must say so rather than appearing broken.
            expiry = record.artifacts_expire_at
            tooltip = f"Artifacts removed on {expiry:%Y-%m-%d}" if expiry else "Artifacts removed"
            return format_html(
                '{} <span class="badge text-bg-secondary ms-1" title="{}">Artifacts removed</span>',
                badge,
                tooltip,
            )
        return badge

    def render_elapsed(self, record: SBOMJob) -> str:
        """Elapsed wall-clock time: live while running, frozen once finished (Story 6.3).

        A running job is measured against *now*, so each poll advances it; a finished job uses
        its recorded ``completed_at`` and therefore stops moving. The freeze is a consequence
        of the data, not of stopping a timer.
        """
        end = record.completed_at or timezone.now()
        return format_duration((end - record.created_at).total_seconds())

    def render_results(self, record: SBOMJob) -> SafeString:
        """Link to the job's results page."""
        return format_html('<a href="{}">View</a>', reverse("ui-job-results", kwargs={"task_id": record.task_id}))


def _artifacts_purged(job: SBOMJob) -> bool:
    """Return True if a completed job's artifacts have been removed (Story 7.3).

    Mirrors ``HistoryPage.tsx``: ``expired = status === 'SUCCESS' && !artifactsAvailable``.
    A job that never succeeded has no artifacts to have lost.
    """
    return bool(job.status == SBOMJob.Status.SUCCESS and not job.result_key)


class SbomComponentTable(tables.Table):
    """The generated SBOM's components (converted from ``SbomTab.tsx``).

    Fed the **already-enriched** dicts the document carries — licence (Story 8.25),
    ecosystem and purl type (Story 8.26), direct/transitive relationship (Stories 8.3-8.4).
    The SBOM is never re-parsed to build this table; the enrichment was written at generation
    time and is read back as-is.

    Sorting is server-side via ``?sort=``, a deliberate change from the SPA's in-browser sort:
    it costs a round trip but makes a sorted view linkable.
    """

    name = tables.Column(verbose_name="Name")
    version = tables.Column(verbose_name="Version", default="—")
    type = tables.Column(verbose_name="Type", default="—")
    license = tables.Column(verbose_name="License", default="—")
    relationship = tables.Column(verbose_name="Relationship", default="—")
    ecosystem = tables.Column(verbose_name="Ecosystem", default="—")

    class Meta:
        # Story 8.16: name ascending is the default sort, matching the SPA.
        order_by = "name"
        attrs = {"class": "table table-sm align-middle"}  # noqa: RUF012  # tables2 Meta option
        empty_text = "This SBOM lists no components."

    def __init__(self, data: list[dict[str, Any]], *args: Any, **kwargs: Any) -> None:
        """Hide the Relationship column when no component carries one.

        Mirrors the SPA's `showRelationship`: direct/transitive data only exists for formats
        and runs where resolution captured it, and an all-em-dash column is worse than none.
        """
        super().__init__(data, *args, **kwargs)
        if not any(row.get("relationship") for row in data):
            self.columns.hide("relationship")
