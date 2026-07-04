"""Manifest upload model (F3).

Stores an uploaded dependency manifest plus the required provenance metadata
(FR-3.8) that is later embedded in the generated SBOM's document metadata.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from generate_sbom.common.models import OrgScopedModel


def manifest_upload_path(instance: ManifestUpload, filename: str) -> str:
    """Return the storage key: manifest-uploads/{org_id}/{upload_id}/{filename}."""
    return f"manifest-uploads/{instance.org_id}/{instance.pk}/{filename}"


class ManifestUpload(OrgScopedModel):
    """An uploaded manifest/lock file with detected format and provenance."""

    class Format(models.TextChoices):
        REQUIREMENTS = "requirements", "requirements.txt"
        PYPROJECT = "pyproject", "pyproject.toml"
        PIXI_LOCK = "pixi_lock", "pixi.lock"
        PIXI_TOML = "pixi_toml", "pixi.toml"
        CONDA = "conda", "conda environment.yml"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Nullable: programmatic (API-key) uploads have an org but no user, matching
    # SBOMJob.user. SET_NULL keeps an org's uploads if the uploading user is removed.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manifest_uploads",
    )
    file = models.FileField(upload_to=manifest_upload_path)
    detected_format = models.CharField(max_length=20, choices=Format.choices)
    original_filename = models.CharField(max_length=255)

    # Provenance metadata (FR-3.8, all required).
    application_id = models.CharField(max_length=255)
    component_name = models.CharField(max_length=255)
    repository_url = models.URLField(max_length=500)
    source_branch = models.CharField(max_length=255)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """Return a readable summary of the upload."""
        return f"{self.original_filename} ({self.detected_format})"
