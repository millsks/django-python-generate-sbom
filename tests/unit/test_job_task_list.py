"""Story 22.20: the pipeline reports as a list of tasks, not a single status line.

Supersedes the mechanism from Story 22.19 (`advance_job_progress` and the `current_step`
string), which could not be made to work: the three analysis tasks run concurrently in a chord,
so a single "current step" can only ever name one of them, and the hand-picked percentage bands
had drifted until two different tasks both claimed 93%. The bar and the label disagreed because
the data model could not express what was actually happening.

A row per task per job fixes both. Each task writes **only its own row**, so concurrency is not
a race; the bar is **derived** from how many rows have finished, so a task cannot pick its own
number and two tasks cannot claim the same point.
"""

from __future__ import annotations

import pytest

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import JobTask, SBOMJob
from inventory.sbom.pipeline_tasks import PIPELINE_TASKS, TASK_COUNT, progress_for
from inventory.sbom.services import (
    create_job,
    finish_job_task,
    seed_job_tasks,
    start_job_task,
)
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
    return create_job(default_org, upload, None, "cyclonedx-json")


def _reload(job: SBOMJob) -> SBOMJob:
    job.refresh_from_db()
    return job


def _states(job: SBOMJob) -> dict[str, str]:
    return {task.key: task.state for task in job.tasks.all()}


# --- The sequence is declared once ---------------------------------------------------------


def test_every_task_gets_an_equal_share() -> None:
    """The property the old hand-picked bands never had.

    5/20/45/55/80/93/95/97 were guesses that drifted; two tasks ended up both reporting 93%,
    which is what let the bar and the label disagree. Deriving the share means adding a task
    cannot silently overweight the others.
    """
    shares = [progress_for(n + 1) - progress_for(n) for n in range(TASK_COUNT)]

    assert progress_for(0) == 0
    assert progress_for(TASK_COUNT) == 100
    assert max(shares) - min(shares) <= 1, f"shares should be even, got {shares}"


def test_the_ordinals_are_contiguous_and_unique() -> None:
    """Display order is the list's own business; a gap or a duplicate would misorder the page."""
    ordinals = [task.ordinal for task in PIPELINE_TASKS]

    assert ordinals == list(range(1, TASK_COUNT + 1))
    assert len({task.key for task in PIPELINE_TASKS}) == TASK_COUNT


def test_progress_cannot_exceed_one_hundred() -> None:
    """A caller counting rows must never be able to render a 110% bar."""
    assert progress_for(TASK_COUNT + 5) == 100
    assert progress_for(-3) == 0


# --- Seeding ---------------------------------------------------------------------------------


def test_a_new_job_lists_its_whole_pipeline(job: SBOMJob) -> None:
    """Seeded up front so the page shows what is *coming*, not only what has happened."""
    tasks = list(job.tasks.all())

    assert len(tasks) == TASK_COUNT
    assert all(task.state == JobTask.State.PENDING for task in tasks)
    assert [task.ordinal for task in tasks] == list(range(1, TASK_COUNT + 1))


def test_seeding_twice_does_not_duplicate(job: SBOMJob) -> None:
    """The unique constraint is the real guard; this proves seeding is safe to retry."""
    seed_job_tasks(job)

    assert job.tasks.count() == TASK_COUNT


# --- Running and finishing ---------------------------------------------------------------------


def test_starting_a_task_marks_it_running_and_stamps_the_time(job: SBOMJob) -> None:
    """The stamp is what the browser animates the dots from, so its absence is a real bug."""
    start_job_task(str(job.task_id), "detect")

    task = job.tasks.get(key="detect")
    assert task.state == JobTask.State.RUNNING
    assert task.started_at is not None


def test_the_bar_only_moves_when_a_task_finishes(job: SBOMJob) -> None:
    """Starting work is not progress. The bar answers "how much is done", not "is anything on"."""
    start_job_task(str(job.task_id), "detect")
    assert _reload(job).progress == 0

    finish_job_task(str(job.task_id), "detect")
    assert _reload(job).progress == progress_for(1)


def test_two_tasks_can_run_at_once(job: SBOMJob) -> None:
    """The whole reason this is a table: a chord really does run three tasks together.

    The old single `current_step` string could name only one of them, which is why the display
    kept disagreeing with itself.
    """
    for key in ("vuln", "license", "version"):
        start_job_task(str(job.task_id), key)

    running = [key for key, state in _states(job).items() if state == JobTask.State.RUNNING]
    assert sorted(running) == ["license", "version", "vuln"]


def test_concurrent_tasks_do_not_overwrite_each_other(job: SBOMJob) -> None:
    """Each task writes only its own row, so interleaving cannot corrupt a neighbour."""
    start_job_task(str(job.task_id), "vuln")
    start_job_task(str(job.task_id), "license")
    finish_job_task(str(job.task_id), "vuln")

    states = _states(job)
    assert states["vuln"] == JobTask.State.COMPLETE
    assert states["license"] == JobTask.State.RUNNING
    assert _reload(job).progress == progress_for(1)


def test_a_failed_task_is_marked_error_and_still_advances_the_bar(job: SBOMJob) -> None:
    """FR-4.5 keeps the job running when an analysis task fails.

    A bar that stalled on the failure would misreport a job that is still working, and a task
    list that showed it as still running would be worse — so it reads [ERROR] and counts.
    """
    finish_job_task(str(job.task_id), "vuln", failed=True, detail="offline")

    task = job.tasks.get(key="vuln")
    assert task.state == JobTask.State.ERROR
    assert task.detail == "offline"
    assert _reload(job).progress == progress_for(1)


def test_a_finished_job_is_not_dragged_back_into_progress(job: SBOMJob) -> None:
    """A straggling group member must not un-finish a job the chord callback already closed."""
    SBOMJob.objects.filter(pk=job.pk).update(status=SBOMJob.Status.SUCCESS, progress=100)

    finish_job_task(str(job.task_id), "license")

    updated = _reload(job)
    assert updated.status == SBOMJob.Status.SUCCESS
    assert updated.progress == 100


def test_an_unknown_task_key_is_a_no_op(job: SBOMJob) -> None:
    """Reporting must never be the thing that raises inside a phase."""
    start_job_task(str(job.task_id), "not-a-task")
    finish_job_task(str(job.task_id), "not-a-task")

    assert _reload(job).progress == 0


# --- How it renders ---------------------------------------------------------------------------


def _panel(job: SBOMJob) -> str:
    from django.test import Client

    return Client().get(f"/results/{job.task_id}/progress").content.decode()


def test_the_panel_lists_every_task_with_the_requested_prefix(job: SBOMJob) -> None:
    """`escape` because "Detect & parse manifest" renders as `&amp;` — comparing raw would
    fail on the one label containing an ampersand and pass on the other seven."""
    from django.utils.html import escape

    body = _panel(job)

    for task in PIPELINE_TASKS:
        assert f"Task: {escape(task.label)}" in body, task.label


def test_a_running_task_shows_dots_and_a_finished_one_shows_its_outcome(job: SBOMJob) -> None:
    start_job_task(str(job.task_id), "vuln")
    finish_job_task(str(job.task_id), "detect")
    finish_job_task(str(job.task_id), "resolve", failed=True, detail="resolution_failed")

    body = _panel(job)

    assert "data-task-dots" in body, "the running task should animate"
    assert "[COMPLETE]" in body
    assert "[ERROR]" in body
    assert "resolution_failed" in body


def test_each_running_task_carries_the_key_its_dots_are_counted_by(job: SBOMJob) -> None:
    """The count is kept in the script, keyed by task, not in the swapped markup.

    Deriving it from a start timestamp was tried first and read badly: a task already running
    when its row appeared started mid-cycle, concurrent tasks each showed a different count, and
    clock skew shifted everything — the dots jumped instead of counting. A key plus a counter
    in the script gives a plain 0-to-10 sequence that the five-second swap cannot disturb.
    """
    start_job_task(str(job.task_id), "vuln")

    body = _panel(job)

    assert 'data-task-key="vuln"' in body
    assert "data-task-started" not in body, "the timestamp approach was replaced, not layered on"


def test_a_pending_task_shows_neither_dots_nor_an_outcome(job: SBOMJob) -> None:
    """Work that has not begun must not look like work that has."""
    body = _panel(job)

    assert "[COMPLETE]" not in body
    assert "[ERROR]" not in body
    assert "data-task-dots" not in body


def test_the_bar_reports_the_finished_share(job: SBOMJob) -> None:
    finish_job_task(str(job.task_id), "detect")
    finish_job_task(str(job.task_id), "resolve")

    body = _panel(job)

    assert f'aria-valuenow="{progress_for(2)}"' in body


def test_the_dots_script_is_served_and_loaded_outside_the_swapped_fragment() -> None:
    """If it were inside the fragment, every 5s swap would re-run it and restart the animation."""
    from pathlib import Path

    from django.test import Client

    src = Path(__file__).resolve().parents[2] / "src"
    assert (src / "django_service/static/js/task-dots.js").exists()

    shell = Client().get("/ui/").content.decode()
    assert "task-dots.js" in shell

    fragment = (src / "django_apps/inventory/templates/inventory/sbom/_job_progress.html").read_text(encoding="utf-8")
    assert "<script" not in fragment


def test_the_compact_row_still_names_a_running_task(job: SBOMJob) -> None:
    """The Job Status *table* has one cell per job, not room for a list.

    `current_step` is therefore kept in step as a summary — and `current_phase` in the API's
    status payload reads from it, which Story 21.24 AC #9 froze. Dropping it when the list
    arrived would have left every row reading "Queued" for the whole run.
    """
    from django.test import Client

    start_job_task(str(job.task_id), "vuln")

    assert _reload(job).current_step == "Vulnerability scan"

    row = Client().get(f"/job-status/row/{job.task_id}").content.decode()
    assert "Vulnerability scan" in row


def test_the_api_status_payload_still_carries_the_phase(job: SBOMJob) -> None:
    """The frozen `/api/v1/sbom/status/{id}/` shape must not lose a field to this change."""
    from django.test import Client

    start_job_task(str(job.task_id), "generate")

    body = Client().get(f"/api/v1/sbom/status/{job.task_id}/").json()

    assert body["current_phase"] == "Generate SBOM document"
    assert body["progress"] == 0


def test_the_dots_never_blank_and_run_one_to_ten() -> None:
    """Three separate blanking bugs were reported here; this pins all of them at once.

    The animation is entirely client-side, so no server response can show it. The behaviour is
    therefore simulated against the same arithmetic the script uses, including the five-second
    htmx swap that caused the last one:

    * deriving the count from a start timestamp made it jump;
    * a 0..10 cycle blanked the line for a second each pass;
    * a dwell on the tenth dot read as a stall before the restart;
    * and the swap replaced the span with an empty one, so the dots vanished at 5 and returned
      at 6 — the 5 being the poll interval, not the cycle.
    """
    from pathlib import Path

    source = (Path(__file__).resolve().parents[2] / "src/django_service/static/js/task-dots.js").read_text(
        encoding="utf-8"
    )

    assert "htmx:afterSwap" in source, "the swap must trigger a repaint or the dots blank"
    assert "render(false)" in source, "the repaint must not advance the counter"

    max_dots = 10
    counters: dict[str, int] = {}

    def render(advance: bool, key: str = "vuln") -> int:
        step = counters.get(key)
        if step is None:
            step = 0
        elif advance:
            step = (step + 1) % max_dots
        counters[key] = step
        return step + 1

    rendered = []
    for tick in range(1, 26):
        rendered.append(render(True))
        if tick % 5 == 0:  # the htmx swap repaints without advancing
            rendered.append(render(False))

    assert 0 not in rendered, "nothing may render blank"
    # The doubled 5 and 10 are the swap repaints holding the count, not blanks — which is the
    # whole point. After ten the cycle returns straight to one, with no dwell.
    assert rendered[:13] == [1, 2, 3, 4, 5, 5, 6, 7, 8, 9, 10, 10, 1], rendered[:13]
    assert max(rendered) == max_dots


# --- Reporting must never cost the job ------------------------------------------------------


def test_a_reporting_failure_does_not_abort_the_phase(job: SBOMJob) -> None:
    """The bug a developer hit by pulling migration 0004 without running it.

    `start_job_task` is called from `_phase_guard` **before** its `try`, so anything it raised
    propagated out of the context manager's entry and skipped every failure path the guard
    exists to provide. The phase died, the job was never marked FAILED, and it sat at PENDING
    showing "Queued" — a silent stall with nothing to explain it.

    Telemetry is not the work.
    """
    from unittest.mock import patch

    from django.db import OperationalError

    from inventory.tasks.sbom_pipeline import detect_and_parse_manifest

    with patch(
        "inventory.sbom.services._upsert_task",
        side_effect=OperationalError("no such table: inventory_jobtask"),
    ):
        result = detect_and_parse_manifest.apply(args=(str(job.task_id),)).get()

    assert result["task_id"] == str(job.task_id), "the phase must still do its work"


def test_a_reporting_failure_is_logged_rather_than_swallowed(job: SBOMJob) -> None:
    """Broad exception handling earns its keep only if it says something happened."""
    from unittest.mock import patch

    from django.db import OperationalError

    with (
        patch("inventory.sbom.services._upsert_task", side_effect=OperationalError("boom")),
        patch("inventory.sbom.services.logger") as log,
    ):
        start_job_task(str(job.task_id), "detect")

    assert log.error.called
    assert log.error.call_args[0][0] == "job_progress_report_failed"


def test_seeding_failure_does_not_block_job_creation(default_org: Org) -> None:
    """A job that cannot be *displayed* is far better than a job that cannot be *submitted*."""
    from unittest.mock import patch

    from django.db import OperationalError

    upload = ManifestUpload.objects.create(
        org=default_org,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
    )

    with patch("inventory.sbom.services.JobTask.objects.bulk_create", side_effect=OperationalError("boom")):
        created = create_job(default_org, upload, None, "cyclonedx-json")

    assert created.pk is not None


def test_a_failed_job_keeps_the_progress_it_reached(job: SBOMJob) -> None:
    """`update_job_status`'s old defaults reset progress to 0 and blanked the phase.

    Every caller is a failure path passing only a reason, so a job that died at 62% on version
    currency rendered as 0% with no phase — discarding exactly what someone reading a failed
    job wants to know: how far it got and what it was doing.
    """
    from inventory.sbom.services import update_job_status

    finish_job_task(str(job.task_id), "detect")
    start_job_task(str(job.task_id), "resolve")
    reached = _reload(job).progress

    update_job_status(str(job.task_id), SBOMJob.Status.FAILED, failure_reason="resolution_failed")

    updated = _reload(job)
    assert updated.status == SBOMJob.Status.FAILED
    assert updated.failure_reason == "resolution_failed"
    assert updated.progress == reached, "a failed job should still show how far it got"
    assert updated.current_step == "Resolve dependencies", "and what it was doing when it died"
