"""Analysis report persistence (F5).

``AnalysisReport`` is NOT org-scoped directly: org isolation is transitive through
its parent ``SBOMJob`` (reached only via ``SBOMJob.objects.for_org(org)``). Only
the artifact key lives in PostgreSQL; report blobs live in S3 (AD-6).
"""

from __future__ import annotations

from django.db import models


class AnalysisReport(models.Model):
    """One analysis phase's result for a job (vuln / license / version)."""

    class ReportType(models.TextChoices):
        VULN = "vuln", "Vulnerability"
        LICENSE = "license", "License"
        VERSION = "version", "Version currency"

    job = models.ForeignKey("sbom.SBOMJob", on_delete=models.CASCADE, related_name="reports")
    report_type = models.CharField(max_length=10, choices=ReportType.choices)
    artifact_key = models.CharField(max_length=500, null=True, blank=True)
    summary = models.JSONField(default=dict)
    generated_at = models.DateTimeField(auto_now_add=True)
    failed = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        constraints = [  # noqa: RUF012  # Django Meta option, not a mutable dataclass default
            models.UniqueConstraint(fields=["job", "report_type"], name="uniq_job_report_type"),
        ]

    def __str__(self) -> str:
        """Return a readable report summary."""
        state = "failed" if self.failed else "ok"
        return f"AnalysisReport {self.report_type} for {self.job_id} ({state})"
