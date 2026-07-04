"""SBOM job model (F4)."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from generate_sbom.common.models import OrgScopedModel


class SBOMJob(OrgScopedModel):
    """An async SBOM generation job. ``status`` is written only by task code (AD-12)."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROGRESS = "PROGRESS", "In progress"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manifest = models.ForeignKey("manifests.ManifestUpload", on_delete=models.CASCADE, related_name="jobs")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sbom_jobs",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    progress = models.PositiveSmallIntegerField(default=0)
    current_step = models.CharField(max_length=100, default="")
    output_format = models.CharField(max_length=20)  # internal serializer id
    result_key = models.CharField(max_length=500, null=True, blank=True)
    summary_stats = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    artifacts_expire_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self) -> str:
        """Return a readable job summary."""
        return f"SBOMJob {self.task_id} ({self.status})"
