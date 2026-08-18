"""Reading a job's analysis report for the server-rendered tabs (Story 21.14).

**Three distinct states, deliberately not collapsed.** Conflating any two of them is the
likeliest defect in these tabs, and the SPA kept them apart:

- ``FAILED`` — the phase ran and errored, and carries a reason. The other tabs and the SBOM
  download remain usable (FR-6.7), so the tab shows a notice explaining *why*.
- ``MISSING`` — there is no report at all: the phase never ran, or the artifact was purged.
- ``OK`` — the report exists and was read; it may legitimately contain **no findings**, which
  is a clean result, not an empty one.

Shared by Stories 21.14, 21.15 and 21.16 so all three tabs answer "is there a report?" the
same way.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from django.core.files.storage import default_storage

from inventory.sbom.models import SBOMJob

from .models import AnalysisReport


class ReportState(Enum):
    """Why a tab can or cannot render content."""

    OK = "ok"
    MISSING = "missing"
    FAILED = "failed"


@dataclass(frozen=True)
class ReportResult:
    """A report read attempt: its state, its data when readable, its reason when failed."""

    state: ReportState
    data: dict[str, Any] | None = None
    failure_reason: str | None = None

    @property
    def ok(self) -> bool:
        """True when there is content to render."""
        return self.state is ReportState.OK

    @property
    def failed(self) -> bool:
        """True when the phase errored and a reason should be shown."""
        return self.state is ReportState.FAILED


def read_report(job: SBOMJob, report_type: str) -> ReportResult:
    """Read one analysis report for a job.

    Mirrors the DRF endpoint's availability rules — a failed report reports its reason, a
    missing one does not — so the HTML tab and the JSON endpoint agree on what exists.

    Args:
        job: The job whose report to read.
        report_type: One of ``AnalysisReport.ReportType``'s values.

    Returns:
        The read result. ``MISSING`` covers both "no row" and "row without a readable
        artifact", because the tab has nothing to show in either case.
    """
    report = AnalysisReport.objects.filter(job=job, report_type=report_type).first()
    if report is None:
        return ReportResult(ReportState.MISSING)
    if report.failed:
        # Checked BEFORE the artifact: a failed phase has a reason worth showing even though
        # it also has no artifact, and reporting it as merely "missing" would lose that.
        return ReportResult(ReportState.FAILED, failure_reason=report.failure_reason)
    if not report.artifact_key or not default_storage.exists(report.artifact_key):
        return ReportResult(ReportState.MISSING)
    with default_storage.open(report.artifact_key) as handle:
        data = json.loads(handle.read())
    return ReportResult(ReportState.OK, data=data if isinstance(data, dict) else {})
