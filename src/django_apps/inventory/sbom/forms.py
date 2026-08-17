"""Forms for the server-rendered SBOM pages (Story 21.9)."""

from __future__ import annotations

from typing import Any

from django import forms

# The one definition of the 50 MB cap (FR-3.4); imported rather than restated so the
# form and the API serializers cannot disagree about the limit.
from inventory.manifests.serializers import MAX_MANIFEST_BYTES

from .services import DEFAULT_OUTPUT_FORMAT, OUTPUT_FORMAT_CHOICES


class ManifestUploadForm(forms.Form):
    """Upload a manifest and submit an SBOM job (converted from ``UploadPage.tsx``).

    The five provenance fields are all required, exactly as they are in the SPA and in
    ``GenerateJobSerializer`` — FR-3.8 requires them for the generated document's metadata.

    The output-format choices come from :data:`OUTPUT_FORMAT_CHOICES`, which is derived from
    the backend's own ``OUTPUT_FORMAT_MAP``. Story 6.4 was caused by the frontend keeping its
    own copy of a choice list that drifted from the backend's, so this form cannot offer a
    value the backend would reject — the list has one definition.
    """

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

    def clean_file(self) -> Any:
        """Reject oversized uploads with the same limit and wording as the API (FR-3.4)."""
        uploaded = self.cleaned_data["file"]
        if getattr(uploaded, "size", 0) > MAX_MANIFEST_BYTES:
            raise forms.ValidationError("File exceeds the 50 MB limit.")
        return uploaded
