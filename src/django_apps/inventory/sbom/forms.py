"""Forms for the server-rendered SBOM pages (Story 21.9)."""

from __future__ import annotations

from typing import Any

from django import forms

# The one definition of the 50 MB cap (FR-3.4); imported rather than restated so the
# form and the API serializers cannot disagree about the limit.
from inventory.manifests.serializers import MAX_MANIFEST_BYTES
from inventory.users.models import Org
from inventory.users.selectors import get_switchable_orgs

from .services import DEFAULT_OUTPUT_FORMAT, OUTPUT_FORMAT_CHOICES


class ManifestUploadForm(forms.Form):
    """Upload a manifest and submit an SBOM job (converted from ``UploadPage.tsx``).

    The five provenance fields are all required, exactly as they are in the SPA and in
    ``GenerateJobSerializer`` — FR-3.8 requires them for the generated document's metadata.

    The output-format choices come from :data:`OUTPUT_FORMAT_CHOICES`, which is derived from
    the backend's own ``OUTPUT_FORMAT_MAP``. Story 6.4 was caused by the frontend keeping its
    own copy of a choice list that drifted from the backend's, so this form cannot offer a
    value the backend would reject — the list has one definition.

    The **organization** field is chosen explicitly rather than taken from the session. With
    the login removed (Story 21.24) there is no principal whose "active org" could be
    implied, and an SBOM is filed against a tenant permanently — so the choice belongs on the
    form where it is visible at submission time, not in a header dropdown two clicks away.
    Its options come from ``get_switchable_orgs``, the same selector the org switcher uses,
    so the two can never offer different sets.
    """

    #: Resolved per instance rather than at class definition: the queryset must be evaluated
    #: per request, and orgs are created at runtime.
    org = forms.ModelChoiceField(
        queryset=Org.objects.none(),
        label="Organization",
        empty_label=None,
        help_text="The organization this SBOM will belong to.",
    )
    file = forms.FileField(
        label="Manifest file",
        help_text="requirements.txt, pyproject.toml, pixi.lock, pixi.toml, or a conda environment.yml.",
    )
    application_id = forms.CharField(max_length=255, label="Application ID")
    component_name = forms.CharField(max_length=255, label="Component name")
    # URLField, matching the SPA's type="url" and the serializer's URLField — the validation
    # is at least as strict as what it replaces.
    repository_url = forms.URLField(max_length=500, label="Repository URL")
    source_branch = forms.CharField(max_length=255, label="Source branch", initial="main")
    output_format = forms.ChoiceField(
        choices=OUTPUT_FORMAT_CHOICES,
        initial=DEFAULT_OUTPUT_FORMAT,
        label="Output format",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Populate the organization choices and preselect the acting org.

        ``initial`` is set here rather than by the caller so every entry point — the page,
        a re-rendered invalid form — preselects the same thing without repeating itself.
        """
        active_org = kwargs.pop("active_org", None)
        super().__init__(*args, **kwargs)
        self.fields["org"].queryset = get_switchable_orgs()  # type: ignore[attr-defined]
        if active_org is not None and not self.is_bound:
            self.fields["org"].initial = active_org.pk

    def clean_file(self) -> Any:
        """Reject oversized uploads with the same limit and wording as the API (FR-3.4)."""
        uploaded = self.cleaned_data["file"]
        if getattr(uploaded, "size", 0) > MAX_MANIFEST_BYTES:
            raise forms.ValidationError("File exceeds the 50 MB limit.")
        return uploaded
