"""Server-rendered SBOM pages (Story 21.9 onward).

Separate from ``views.py``, which the file-role convention reserves for DRF views. These
render HTML and call the same services the API calls — directly, never over HTTP (AD-1).
"""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from inventory.common.access import OrgAdminRequiredMixin, OrgMemberRequiredMixin
from inventory.common.users import UserT
from inventory.manifests.detection import ManifestParseError, UnsupportedFormatError

from .filters import JobFilterSet
from .forms import ManifestUploadForm
from .models import SBOMJob
from .selectors import get_jobs
from .services import ConcurrencyLimitError, delete_artifacts_for_jobs, submit_job
from .tables import JobTable


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
        # The results path is still owned by the SPA catch-all until Story 21.12 converts it,
        # so this is a literal path rather than a {% url %} reverse. 21.12 swaps it for
        # `reverse("ui-job-results", ...)` when the server-rendered page exists — the same
        # one-at-a-time handover the nav uses.
        return HttpResponseRedirect(f"/results/{job.task_id}")

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
