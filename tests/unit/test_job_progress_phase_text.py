"""Story 22.19: the progress text names the phase actually being worked on.

The Job Status row and the results page both render `SBOMJob.current_step` above the progress
bar, and have since Story 6.2 — but **the analysis phases never wrote it**. Phases 4, 5 and 7
reported progress to Celery's result backend via `task.update_state` and stopped there, while
only the pipeline phases mirrored it to the job row.

The visible effect is the whole reason this story exists: a job sat at *"generate SBOM
document — 45%"* for the entire analysis fan-out, which on a real manifest is the longest part
of the run. The bar looked stuck precisely when the most work was happening.

Two things make this harder than "add a write":

1. **The three analysis phases run concurrently** (a chord group), so whichever finishes a
   write last would win — and their progress bands are 55, 80 and 93, so a naive write can
   move the bar *backwards*.
2. **Phase 8 reports 95 and 97**, which are *below* version currency's 97 end. Mirroring the
   analysis phases exposes that too.

So progress advances monotonically, enforced in the UPDATE's own WHERE clause rather than by
reading first — two workers writing at once must not be able to interleave into a regression.
"""

from __future__ import annotations

import pytest

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.sbom.services import advance_job_progress
from inventory.users.models import Org

pytestmark = pytest.mark.django_db


@pytest.fixture
def job(default_org: Org) -> SBOMJob:
    upload = ManifestUpload.objects.create(
        org=default_org,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
    )
    return SBOMJob.objects.create(
        org=default_org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.PROGRESS,
    )


def _reload(job: SBOMJob) -> SBOMJob:
    job.refresh_from_db()
    return job


# --- The advance itself -------------------------------------------------------------------


def test_it_records_the_phase_and_the_percentage(job: SBOMJob) -> None:
    advance_job_progress(str(job.task_id), 55, "vulnerability scan")

    updated = _reload(job)
    assert updated.progress == 55
    assert updated.current_step == "vulnerability scan"


def test_the_bar_never_moves_backwards_but_the_label_still_follows(job: SBOMJob) -> None:
    """The two halves have different rules, and this is why.

    Version currency starts at 93 and vulnerability scan at 55. The chord does not order its
    group, so the low band can be written after the high one — a bar that jumps back to 55%
    reads as a bug.

    The **label** must not be guarded the same way, and the first version of this code guarded
    it anyway. Version currency wins that race within milliseconds, so vulnerability scan and
    licence compliance never named themselves at all: a real job traced `45% → 93%` with the
    text frozen on "generate SBOM document", which is the exact complaint this story exists to
    fix. Confirmed against a real worker before and after.
    """
    advance_job_progress(str(job.task_id), 93, "version currency")
    advance_job_progress(str(job.task_id), 55, "vulnerability scan")

    updated = _reload(job)
    assert updated.progress == 93, "the bar holds at the furthest point reached"
    assert updated.current_step == "vulnerability scan", "the label names the most recent phase"


def test_every_analysis_phase_gets_to_name_itself(job: SBOMJob) -> None:
    """The regression that made the fix invisible, pinned as a sequence.

    All three phases start within milliseconds of each other. What a watcher must see is each
    one appear — not only whichever happened to hold the highest percentage.
    """
    labels = []
    for progress, step in [(55, "vulnerability scan"), (93, "version currency"), (80, "license compliance")]:
        advance_job_progress(str(job.task_id), progress, step)
        labels.append(_reload(job).current_step)

    assert labels == ["vulnerability scan", "version currency", "license compliance"]
    assert _reload(job).progress == 93


def test_the_same_percentage_may_still_change_the_label(job: SBOMJob) -> None:
    """Phase 8 persists at 97, and version currency also ends at 97.

    Blocking equal values would leave the text stuck on the analysis phase through the final
    write, so the guard rejects only a genuine regression.
    """
    advance_job_progress(str(job.task_id), 97, "version currency complete")
    advance_job_progress(str(job.task_id), 97, "persist artifacts")

    assert _reload(job).current_step == "persist artifacts"


def test_it_marks_the_job_in_progress(job: SBOMJob) -> None:
    """A queued job that starts reporting must leave PENDING, as `_report` always did."""
    SBOMJob.objects.filter(pk=job.pk).update(status=SBOMJob.Status.PENDING)

    advance_job_progress(str(job.task_id), 5, "detect & parse manifest")

    assert _reload(job).status == SBOMJob.Status.PROGRESS


def test_an_unknown_task_id_is_a_no_op(job: SBOMJob) -> None:
    """Progress reporting must never be the thing that raises inside a phase."""
    advance_job_progress("00000000-0000-0000-0000-000000000000", 55, "vulnerability scan")

    assert _reload(job).progress == 0


def test_a_finished_job_is_not_dragged_back_into_progress(job: SBOMJob) -> None:
    """A late write from a straggling analysis phase must not un-finish a job.

    The chord callback can finalize while a group member is still unwinding, and a job that
    flips back to "In progress" after showing Success is worse than a stale percentage.
    """
    SBOMJob.objects.filter(pk=job.pk).update(status=SBOMJob.Status.SUCCESS, progress=100)

    advance_job_progress(str(job.task_id), 80, "license compliance")

    updated = _reload(job)
    assert updated.status == SBOMJob.Status.SUCCESS
    assert updated.progress == 100


# --- The phases actually use it ------------------------------------------------------------


@pytest.mark.parametrize(
    ("task_name", "expected_step", "start_pct", "end_pct"),
    [
        ("scan_vulnerabilities", "vulnerability scan", 55, 80),
        ("classify_licenses", "license compliance", 80, 88),
        ("check_version_currency", "version currency", 93, 97),
    ],
)
def test_each_analysis_phase_names_itself_before_it_starts_working(
    task_name: str, expected_step: str, start_pct: int, end_pct: int, job: SBOMJob
) -> None:
    """The defect: these three reported to Celery's backend and never to the job row.

    Asserted on the **sequence** of writes rather than on the row afterwards. A phase runs to
    completion synchronously here, so the final state cannot distinguish "named itself when it
    started" from "named itself only when it finished" — and an earlier version of this test
    stayed green with the entry write ablated away, which is how that was found.
    """
    from unittest.mock import patch

    from inventory.tasks import analysis

    calls: list[tuple[int, str]] = []

    with (
        patch("inventory.tasks.analysis.resolve_job_packages", return_value=[]),
        patch(
            "inventory.tasks.analysis.advance_job_progress",
            side_effect=lambda _task_id, progress, step: calls.append((progress, step)),
        ),
    ):
        getattr(analysis, task_name).apply(args=({"task_id": str(job.task_id)},)).get()

    assert calls[0] == (start_pct, expected_step), "the phase must name itself before it works"
    assert calls[-1][0] == end_pct, "and advance to its band's end when done"


def test_a_failed_analysis_phase_does_not_claim_to_have_completed(job: SBOMJob) -> None:
    """FR-4.5 keeps the job running when a phase fails, so the label must stay honest.

    The completion write is outside the try/except on purpose — the bar has to keep moving —
    which means it would otherwise stamp "complete" on a phase that produced nothing.
    "unavailable" is the word the report tabs already use for this state.
    """
    from unittest.mock import patch

    from inventory.tasks import analysis

    with (
        patch("inventory.tasks.analysis.resolve_job_packages", return_value=[]),
        patch("inventory.analysis.services.vulnerability.scan", side_effect=RuntimeError("offline")),
    ):
        envelope = analysis.scan_vulnerabilities.apply(args=({"task_id": str(job.task_id)},)).get()

    updated = _reload(job)
    assert envelope["failed"] is True
    assert updated.current_step == "vulnerability scan unavailable"
    assert updated.progress == 80, "a failed phase still advances the bar (FR-4.5)"


def test_a_successful_phase_says_complete(job: SBOMJob) -> None:
    """The other side of the same label, so "unavailable" cannot quietly become the only word."""
    from unittest.mock import patch

    from inventory.tasks import analysis

    with (
        patch("inventory.tasks.analysis.resolve_job_packages", return_value=[]),
        patch(
            "inventory.analysis.services.vulnerability.scan",
            return_value={"packages": [], "summary": {}},
        ),
    ):
        analysis.scan_vulnerabilities.apply(args=({"task_id": str(job.task_id)},)).get()

    assert _reload(job).current_step == "vulnerability scan complete"


# --- How it reads on the page ----------------------------------------------------------------


def test_the_row_shows_the_phase_above_the_bar(job: SBOMJob) -> None:
    """End to end: the write reaches the markup a user actually polls."""
    from django.test import Client

    advance_job_progress(str(job.task_id), 55, "vulnerability scan")

    body = Client().get(f"/job-status/row/{job.task_id}").content.decode()

    assert "Vulnerability scan" in body
    assert 'aria-valuenow="55"' in body


def test_the_results_page_progress_panel_shows_it_too(job: SBOMJob) -> None:
    from django.test import Client

    advance_job_progress(str(job.task_id), 80, "license compliance")

    body = Client().get(f"/results/{job.task_id}/progress").content.decode()

    assert "License compliance" in body
    assert 'aria-valuenow="80"' in body


def test_a_phase_name_containing_sbom_is_not_mangled(job: SBOMJob) -> None:
    """`capfirst`, not `title` — the latter turns "generate SBOM document" into "Sbom"."""
    from django.test import Client

    advance_job_progress(str(job.task_id), 45, "generate SBOM document")

    body = Client().get(f"/job-status/row/{job.task_id}").content.decode()

    assert "Generate SBOM document" in body


def test_a_job_with_no_phase_yet_reads_as_queued(job: SBOMJob) -> None:
    from django.test import Client

    SBOMJob.objects.filter(pk=job.pk).update(status=SBOMJob.Status.PENDING, current_step="")

    body = Client().get(f"/job-status/row/{job.task_id}").content.decode()

    assert "Queued" in body
