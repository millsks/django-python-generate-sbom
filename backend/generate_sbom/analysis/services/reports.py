"""Analysis chord-envelope + report-persistence helpers (Story 4.1).

Each analysis task returns the standard envelope; the 4.6 chord callback reads it
to persist an ``AnalysisReport``. Report blobs live in S3; only the artifact key
is stored in PostgreSQL (AD-6).
"""

from __future__ import annotations

from typing import Any

from generate_sbom.sbom.models import SBOMJob

from ..models import AnalysisReport


def make_envelope(
    report_type: str,
    *,
    artifact_key: str | None = None,
    summary: dict[str, Any] | None = None,
    failed: bool = False,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    """Build the standard analysis chord envelope (AD-4 convention)."""
    return {
        "report_type": report_type,
        "artifact_key": artifact_key,
        "summary": summary if summary is not None else {},
        "failed": failed,
        "failure_reason": failure_reason,
    }


def write_report(job: SBOMJob, envelope: dict[str, Any]) -> AnalysisReport:
    """Upsert an ``AnalysisReport`` row from a chord envelope (used by the 4.6 callback).

    Keyed on (job, report_type) so a chord re-run overwrites rather than conflicting
    with the unique constraint.
    """
    report, _ = AnalysisReport.objects.update_or_create(
        job=job,
        report_type=envelope["report_type"],
        defaults={
            "artifact_key": envelope["artifact_key"],
            "summary": envelope["summary"],
            "failed": envelope["failed"],
            "failure_reason": envelope["failure_reason"],
        },
    )
    return report
