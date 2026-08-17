"""Server-rendered SBOM pages (Story 21.9 onward).

Separate from ``views.py``, which the file-role convention reserves for DRF views. These
render HTML and call the same services the API calls — directly, never over HTTP (AD-1).
"""

from __future__ import annotations

from typing import Any

from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import FormView

from inventory.common.access import OrgMemberRequiredMixin
from inventory.common.users import UserT
from inventory.manifests.detection import ManifestParseError, UnsupportedFormatError

from .forms import ManifestUploadForm
from .services import ConcurrencyLimitError, submit_job


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
