"""Server-rendered SBOM pages (Story 21.9 onward).

Separate from ``views.py``, which the file-role convention reserves for DRF views. These
render HTML and call the same services the API calls — directly, never over HTTP (AD-1).
"""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView
from django_filters.views import FilterView
from django_tables2 import RequestConfig, SingleTableMixin

from inventory.analysis.filters import filter_by_severity
from inventory.analysis.models import AnalysisReport
from inventory.analysis.reports import read_report
from inventory.analysis.tables import (
    SEVERITY_CHOICES,
    VersionTable,
    VulnerabilityTable,
    version_rows,
    vulnerability_rows,
)
from inventory.common.access import OrgAdminRequiredMixin, OrgMemberRequiredMixin
from inventory.common.users import UserT
from inventory.manifests.detection import ManifestParseError, UnsupportedFormatError

from .filters import JobFilterSet
from .forms import ManifestUploadForm
from .models import SBOMJob
from .overview import build_metrics
from .selectors import get_job, get_jobs, read_inline_document
from .services import TERMINAL_STATUSES, ConcurrencyLimitError, delete_artifacts_for_jobs, submit_job
from .tables import JobTable, SbomComponentTable


class UploadPageView(OrgMemberRequiredMixin, FormView):  # type: ignore[type-arg]
    """Upload a manifest and start an SBOM job (converted from ``UploadPage.tsx``).

    ``OrgMemberRequiredMixin`` supplies ``self.org`` and renders the shared zero-org state in
    place of this page for a user with no organisation (AC #6) — nothing here handles that
    case, which is the point of enforcing it at the mixin layer.
    """

    template_name = "inventory/sbom/upload.html"
    form_class = ManifestUploadForm

    def form_valid(self, form: ManifestUploadForm) -> HttpResponse:
        """Submit the job, or re-display the form with the reason it was refused.

        Every invariant — the AD-7 concurrency gate, AD-12's initial ``PENDING`` write, and
        AD-10's ``delay_on_commit`` dispatch — lives in ``submit_job``, which the DRF endpoint
        also calls. None of it is reproduced here, so the web UI and the API cannot diverge
        on the limit or on dispatch semantics.
        """
        user: UserT | None = self.request.user if self.request.user.is_authenticated else None
        try:
            job, _upload = submit_job(
                self.org,
                user,
                file_obj=form.cleaned_data["file"],
                application_id=form.cleaned_data["application_id"],
                component_name=form.cleaned_data["component_name"],
                repository_url=form.cleaned_data["repository_url"],
                source_branch=form.cleaned_data["source_branch"],
                output_format=form.cleaned_data["output_format"],
            )
        except ConcurrencyLimitError as exc:
            # A form-level error: nothing the user typed is wrong, so it belongs to the
            # submission rather than to a field. The message tells them to retry, which is
            # the human form of the API's Retry-After header.
            form.add_error(None, exc.message)
            return self.form_invalid(form)
        except (UnsupportedFormatError, ManifestParseError) as exc:
            # Both are about the uploaded file, so they attach to that field.
            form.add_error("file", str(exc))
            return self.form_invalid(form)

        # POST-redirect-GET (AC #4): a refresh after submitting must not enqueue a second job.
        #
        return HttpResponseRedirect(reverse("ui-job-results", kwargs={"task_id": job.task_id}))

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Expose the active org for the page heading."""
        context = super().get_context_data(**kwargs)
        context["org"] = self.org
        return context


# --- Job history (Story 21.10) -------------------------------------------------------------

#: Matches the SPA's PAGE_SIZE and the API's PageNumberPagination default.
JOBS_PER_PAGE = 25


class JobHistoryView(OrgMemberRequiredMixin, SingleTableMixin, FilterView):
    """Filterable, paginated job history (converted from ``HistoryPage.tsx``).

    Sorting and paging are **server-side**, via the querystring, so a filtered view is
    bookmarkable and shareable. That is a deliberate trade the epic accepted: the SPA sorted
    already-fetched rows in the browser, which cost no round trip but could not be linked to.
    """

    model = SBOMJob
    table_class = JobTable
    filterset_class = JobFilterSet
    template_name = "inventory/sbom/history.html"
    paginate_by = JOBS_PER_PAGE

    def get_queryset(self):  # type: ignore[no-untyped-def]
        """Only the active org's jobs (AD-2), newest first."""
        return get_jobs(self.org)


class _ArtifactDeleteMixin(OrgMemberRequiredMixin):
    """Shared redirect target for the delete actions."""

    def _back(self) -> HttpResponse:
        return HttpResponseRedirect(reverse("ui-history"))


class JobArtifactsDeleteView(_ArtifactDeleteMixin, View):
    """Delete artifacts for one job or for a page selection (Story 7.2, FR-8.2).

    Single and bulk are the same operation with a different number of ids, so they share an
    endpoint rather than duplicating the org scoping.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        """Purge the named jobs' artifacts, keeping every job record."""
        task_ids = request.POST.getlist("task_ids")
        if not task_ids:
            messages.error(request, "Select at least one job.")
            return self._back()

        # Scoped to the active org, so a task id from another org simply matches nothing
        # (AD-2) — there is no branch that could treat it differently.
        jobs = get_jobs(self.org).filter(task_id__in=task_ids, result_key__isnull=False)
        deleted = delete_artifacts_for_jobs(jobs)

        if deleted:
            messages.success(request, f"Deleted artifacts for {deleted} job(s). The job records were kept.")
        else:
            messages.info(request, "Nothing to delete — those jobs have no artifacts.")
        return self._back()


class JobArtifactsDeleteAllView(OrgAdminRequiredMixin, View):
    """Delete every artifact in the active org (FR-8.5) — **admin only**.

    The gate is this mixin, not the hidden button. Story 2.17 exists because an admin-only
    action was once enforced only in the UI, and `test_a_member_cannot_post_the_org_wide_delete`
    is what stops that recurring here.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        """Purge artifacts org-wide, keeping every job record."""
        jobs = get_jobs(self.org).filter(result_key__isnull=False)
        deleted = delete_artifacts_for_jobs(jobs)
        messages.success(request, f"Deleted artifacts for {deleted} job(s). The job records were kept.")
        return HttpResponseRedirect(reverse("ui-history"))


# --- Live progress (Story 21.11) -----------------------------------------------------------


class JobRowPartialView(OrgMemberRequiredMixin, View):
    """Re-render one history row (the polling endpoint for the table).

    Org-scoped through ``get_job``, so a cross-org or unknown task id is a 404 — identical
    responses, no existence leak (AD-2). htmx stops polling on a 404 by default, which is
    exactly the required behaviour: the row is left as it was rather than spinning forever.
    """

    def get(self, request: HttpRequest, task_id: str) -> HttpResponse:
        """Return the row's current markup, with or without a poll trigger."""
        try:
            job = get_job(self.org, task_id)
        except SBOMJob.DoesNotExist as exc:
            raise Http404 from exc
        # Built from the same JobTable as the full table, so every cell renderer — badge,
        # progress bar, elapsed — is shared rather than reimplemented for the partial.
        table = JobTable([job])
        return render(request, "inventory/sbom/_job_row.html", {"table": table})


#: The five tabs, in ResultsPage.tsx's order. `sbom` was inserted at index 1 by Story 8.6 and
#: the Dependency Graph tab was retired by Story 20.1 — this list is the record of that.
RESULT_TABS = (
    ("overview", "Overview"),
    ("sbom", "SBOM"),
    ("vulnerabilities", "Vulnerabilities"),
    ("licenses", "Licenses"),
    ("versions", "Version Currency"),
)

DEFAULT_TAB = "overview"

#: Tabs that need the stored artifacts. When a job's blobs have been purged (Story 7.3) the
#: Overview still renders from summary_stats, but these have nothing to read.
ARTIFACT_TABS = frozenset({"sbom", "vulnerabilities", "licenses", "versions"})


def _resolve_tab(request: HttpRequest) -> str:
    """Return the requested tab, falling back to Overview for anything unrecognised."""
    requested = request.GET.get("tab", DEFAULT_TAB)
    return requested if requested in dict(RESULT_TABS) else DEFAULT_TAB


def _tab_template(tab: str) -> str:
    """Return the partial for a tab. The name is validated before it reaches here."""
    return f"inventory/sbom/tabs/_{tab}.html"


class _JobScopedView(OrgMemberRequiredMixin, View):
    """Look a job up within the active org, 404ing identically for missing and cross-org.

    AD-2: an unauthorised request must be indistinguishable from a nonexistent one — the SPA
    showed a single message for both ("You don't have access to these results, or they don't
    exist"), and the server-rendered path keeps that property by having one code path.
    """

    def get_job_or_404(self, task_id: str) -> SBOMJob:
        """Return the job, or raise Http404."""
        try:
            return get_job(self.org, task_id)
        except SBOMJob.DoesNotExist as exc:
            raise Http404 from exc


class JobResultsView(_JobScopedView):
    """The results page: a progress gate while running, the five-tab shell once finished."""

    def get(self, request: HttpRequest, task_id: str) -> HttpResponse:
        """Render the shell with the requested tab already populated.

        The active tab is rendered server-side rather than fetched, so a bookmarked
        ``?tab=licenses`` survives a refresh with no JavaScript — htmx only handles the
        subsequent in-page switches.
        """
        job = self.get_job_or_404(task_id)
        terminal = job.status in TERMINAL_STATUSES
        active_tab = _resolve_tab(request)
        context: dict[str, Any] = {
            "job": job,
            "org": self.org,
            "job_is_terminal": terminal,
            "tabs": RESULT_TABS,
            "active_tab": active_tab,
            # Rendered server-side so a bookmarked ?tab= survives a refresh with no
            # JavaScript; htmx only avoids a full reload on subsequent clicks.
            "active_tab_template": _tab_template(active_tab),
            "artifacts_available": bool(job.result_key),
            "artifact_tabs": ARTIFACT_TABS,
            "metrics": build_metrics(job.summary_stats),
        }
        context.update(tab_context(request, job, active_tab))
        return render(request, "inventory/sbom/results.html", context)


class JobTabPartialView(_JobScopedView):
    """Render one tab's content, loaded by htmx when a tab is clicked."""

    def get(self, request: HttpRequest, task_id: str, tab: str) -> HttpResponse:
        """Return the tab body, or 404 for an unrecognised tab name."""
        if tab not in dict(RESULT_TABS):
            raise Http404
        job = self.get_job_or_404(task_id)
        context: dict[str, Any] = {
            "job": job,
            "active_tab": tab,
            "artifacts_available": bool(job.result_key),
            "metrics": build_metrics(job.summary_stats),
        }
        context.update(tab_context(request, job, tab))
        return render(request, _tab_template(tab), context)


class JobProgressPartialView(_JobScopedView):
    """The results page's polled fragment.

    Uses the same 5-second convention as the row trigger. When the job terminates this
    responds with an ``HX-Refresh`` header so the page reloads into the full results view
    without a manual refresh — the server decides the transition, not the client.
    """

    def get(self, request: HttpRequest, task_id: str) -> HttpResponse:
        """Return the progress fragment, or ask htmx to reload once the job is done."""
        job = self.get_job_or_404(task_id)
        terminal = job.status in TERMINAL_STATUSES
        response = render(request, "inventory/sbom/_job_progress.html", {"job": job, "job_is_terminal": terminal})
        if terminal:
            response["HX-Refresh"] = "true"
        return response


#: A raw document larger than this is offered as a download instead of being inlined. A
#: multi-megabyte <pre> block makes the results page unusable, and the browser has to hold the
#: whole thing in the DOM — the Dev Notes call the raw view "the size risk".
RAW_INLINE_MAX_BYTES = 2 * 1024 * 1024


def sbom_tab_context(request: HttpRequest, job: SBOMJob) -> dict[str, Any]:
    """Build the SBOM tab's context: the component table, or the unavailable notice.

    The **raw document is deliberately absent**. It is fetched by its own request so a
    multi-megabyte document never rides along in this tab's payload (AC #4).
    """
    document = read_inline_document(job)
    if document is None:
        # Never produced, not finished, or purged — one notice covers all three, which is
        # what the SPA did ("an unavailable/expired artifact shows a notice, not an error").
        return {"sbom_available": False}

    table = SbomComponentTable(document.components)
    # RequestConfig applies ?sort= from the querystring, which is what moves sorting
    # server-side while keeping a sorted view linkable.
    RequestConfig(request, paginate=False).configure(table)
    return {
        "sbom_available": True,
        "sbom_table": table,
        "sbom_metadata": document.metadata,
        "sbom_component_count": len(document.components),
    }


class SbomRawView(_JobScopedView):
    """Serve the raw SBOM text for the viewer's raw mode (loaded on demand).

    Its own endpoint precisely so the document is not part of the SBOM tab's initial payload.
    Above :data:`RAW_INLINE_MAX_BYTES` it declines to inline and points at the download
    instead, rather than shipping megabytes of text into the DOM.

    This is the *inline* read (AD-5) and is distinct from the presigned download (AD-11) —
    the two must not be conflated.
    """

    def get(self, request: HttpRequest, task_id: str) -> HttpResponse:
        """Return the raw document, a too-large notice, or the unavailable notice."""
        job = self.get_job_or_404(task_id)
        document = read_inline_document(job)
        context: dict[str, Any] = {"job": job}
        if document is None:
            context["sbom_available"] = False
        else:
            context["sbom_available"] = True
            context["too_large"] = document.size_bytes > RAW_INLINE_MAX_BYTES
            context["size_bytes"] = document.size_bytes
            if not context["too_large"]:
                context["raw"] = document.raw.decode("utf-8", errors="replace")
        return render(request, "inventory/sbom/tabs/_sbom_raw.html", context)


def vulnerabilities_tab_context(request: HttpRequest, job: SBOMJob) -> dict[str, Any]:
    """Build the Vulnerabilities tab's context (Story 21.14).

    Keeps the three empty-ish states apart, which is the whole point of this tab:

    - a **failed** phase renders the shared notice with its reason;
    - a **missing** report renders the no-data notice;
    - an **ok** report with no findings renders the explicit clean-scan state, which is
      visibly different from "no data" — a clean scan is a result, not an absence.
    """
    result = read_report(job, AnalysisReport.ReportType.VULN)
    if result.failed:
        return {"report_state": "failed", "failure_reason": result.failure_reason}
    if not result.ok:
        return {"report_state": "missing"}

    report = result.data or {}
    rows = vulnerability_rows(report)
    severity = request.GET.get("severity", "")

    if not rows:
        # The scan ran and found nothing. Report the package count so the statement is
        # concrete rather than merely reassuring.
        summary = report.get("summary") or {}
        scanned = job.summary_stats.get("total_packages") or summary.get("vulnerable_package_count") or 0
        return {"report_state": "clean", "scanned_packages": scanned}

    table = VulnerabilityTable(filter_by_severity(rows, severity))
    RequestConfig(request, paginate=False).configure(table)
    return {
        "report_state": "ok",
        "vuln_table": table,
        "severity_choices": SEVERITY_CHOICES,
        "selected_severity": severity,
        "finding_count": len(rows),
    }


def licenses_tab_context(request: HttpRequest, job: SBOMJob) -> dict[str, Any]:
    """Build the Licenses tab's context (Story 21.15).

    The four legal-risk tiers are read **in the order the report supplies them** — the backend
    classifier owns that "descending attention" ordering (Story 4.3). Sorting or naming the
    tiers here would mean a future change to the classification silently renders in the wrong
    order, which is the one thing the Dev Notes warn against.
    """
    result = read_report(job, AnalysisReport.ReportType.LICENSE)
    if result.failed:
        return {"report_state": "failed", "failure_reason": result.failure_reason}
    if not result.ok:
        return {"report_state": "missing"}

    report = result.data or {}
    tiers = [
        {
            "name": tier.get("tier"),
            "packages": tier.get("packages") or [],
            "count": len(tier.get("packages") or []),
        }
        for tier in report.get("tiers") or []
    ]
    return {
        "report_state": "ok",
        "license_tiers": tiers,
        "licensed_package_count": sum(tier["count"] for tier in tiers),
    }


def versions_tab_context(request: HttpRequest, job: SBOMJob) -> dict[str, Any]:
    """Build the Version Currency tab's context (Story 21.16)."""
    result = read_report(job, AnalysisReport.ReportType.VERSION)
    if result.failed:
        return {"report_state": "failed", "failure_reason": result.failure_reason}
    if not result.ok:
        return {"report_state": "missing"}

    rows = version_rows(result.data or {})
    table = VersionTable(rows)
    RequestConfig(request, paginate=False).configure(table)
    return {"report_state": "ok", "version_table": table, "version_package_count": len(rows)}


#: Per-tab context builders. A tab with no entry needs none — the placeholders do not.
TAB_CONTEXT_BUILDERS = {
    "sbom": sbom_tab_context,
    "vulnerabilities": vulnerabilities_tab_context,
    "licenses": licenses_tab_context,
    "versions": versions_tab_context,
}


def tab_context(request: HttpRequest, job: SBOMJob, tab: str) -> dict[str, Any]:
    """Return the extra context a tab needs, or nothing.

    One dispatch point shared by the shell and the htmx partial, so a tab rendered cold from
    ``?tab=`` and the same tab fetched by a click cannot diverge.
    """
    builder = TAB_CONTEXT_BUILDERS.get(tab)
    return builder(request, job) if builder else {}
