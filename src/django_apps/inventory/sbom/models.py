"""SBOM job model (F4)."""

from __future__ import annotations

import uuid
from typing import ClassVar

from django.conf import settings
from django.db import models

from inventory.common.models import OrgScopedModel


class SBOMJob(OrgScopedModel):
    """An async SBOM generation job. ``status`` is written only by task code (AD-12)."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROGRESS = "PROGRESS", "In progress"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manifest = models.ForeignKey("inventory.ManifestUpload", on_delete=models.CASCADE, related_name="jobs")
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


class JobTask(models.Model):
    """One pipeline task's state for one job (Story 22.20).

    A row per task, rather than a JSON blob on ``SBOMJob``, because the three analysis tasks
    run concurrently: each writes **only its own row**, so there is no read-modify-write to
    race on. It also lets the UI show two tasks running at once, which a single
    ``current_step`` string cannot express and which is the honest picture of a chord.

    ``SBOMJob.progress`` is still maintained, derived from how many of these rows have
    finished — the API contract (Story 21.24 AC #9) exposes it and the Job Status table shows
    a compact percentage.
    """

    class State(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETE = "COMPLETE", "Complete"
        ERROR = "ERROR", "Error"

    #: Terminal states — a task in one of these has finished, successfully or not, and counts
    #: toward the bar. FR-4.5 keeps the job going when an analysis task errors, so an errored
    #: task is finished in exactly the sense the bar cares about.
    TERMINAL = (State.COMPLETE, State.ERROR)

    job = models.ForeignKey(SBOMJob, on_delete=models.CASCADE, related_name="tasks")
    key = models.CharField(max_length=32)
    ordinal = models.PositiveSmallIntegerField()
    state = models.CharField(max_length=10, choices=State.choices, default=State.PENDING)
    detail = models.CharField(max_length=200, default="", blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("ordinal",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=("job", "key"), name="uniq_job_task_key")
        ]

    def __str__(self) -> str:
        """Return a readable task summary."""
        return f"{self.key} ({self.state}) for {self.job_id}"

    @property
    def label(self) -> str:
        """The user-facing task name, from the one declaration of the sequence."""
        from .pipeline_tasks import task_label

        return task_label(self.key)

    @property
    def is_running(self) -> bool:
        """Whether this task should show the animated dots."""
        return self.state == self.State.RUNNING
