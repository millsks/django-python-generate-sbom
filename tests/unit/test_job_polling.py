"""Story 21.11: live job progress via htmx polling.

The load-bearing assertions are about when polling **stops**. A poller that never terminates
is the difference between one request per running job and one request per row forever, and it
is invisible in a passing "does it update" test.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org
from inventory.users.services import create_org, register_user

PASSWORD = "pw12345678"
HISTORY = "/history"

# The interval the SPA polled at (POLL_MS = 5000); the conversion must not quietly change it.
EXPECTED_TRIGGER = 'hx-trigger="every 5s"'


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


def _job(org: Org, *, status: str, progress: int = 0, step: str = "", reason: str | None = None) -> SBOMJob:
    upload = ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename=f"{status.lower()}.txt",
        application_id="APP",
        component_name="c",
        repository_url="https://example.com/r",
        source_branch="main",
    )
    job = SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=status,
        progress=progress,
        current_step=step,
        failure_reason=reason,
        result_key="sboms/x.json" if status == SBOMJob.Status.SUCCESS else None,
    )
    if status in (SBOMJob.Status.SUCCESS, SBOMJob.Status.FAILED):
        SBOMJob.objects.filter(pk=job.pk).update(completed_at=job.created_at + timedelta(seconds=42))
        job.refresh_from_db()
    return job


@pytest.fixture
def org_client():  # type: ignore[no-untyped-def]
    user = register_user(email="dev@example.com", password=PASSWORD)
    org = create_org(name="Acme", admin_user=user)
    return _client("dev@example.com"), org


# --- AC #1/#2: only unfinished rows poll --------------------------------------------------


@pytest.mark.django_db
def test_only_non_terminal_rows_carry_a_polling_trigger(org_client) -> None:  # type: ignore[no-untyped-def]
    """The single biggest load difference between this and a naive implementation."""
    client, org = org_client
    running = _job(org, status=SBOMJob.Status.PROGRESS, progress=40, step="Resolving dependencies")
    done = _job(org, status=SBOMJob.Status.SUCCESS)
    failed = _job(org, status=SBOMJob.Status.FAILED, reason="parse_error")

    html = client.get(HISTORY).content.decode()

    assert f"/history/row/{running.task_id}" in html
    assert f"/history/row/{done.task_id}" not in html
    assert f"/history/row/{failed.task_id}" not in html


@pytest.mark.django_db
def test_a_page_of_finished_jobs_issues_no_polling_at_all(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    for _ in range(3):
        _job(org, status=SBOMJob.Status.SUCCESS)

    html = client.get(HISTORY).content.decode()

    assert EXPECTED_TRIGGER not in html


@pytest.mark.django_db
def test_the_poll_interval_matches_the_spa(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    _job(org, status=SBOMJob.Status.PENDING)
    assert EXPECTED_TRIGGER in client.get(HISTORY).content.decode()


@pytest.mark.django_db
def test_the_row_partial_swaps_only_that_row(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    running = _job(org, status=SBOMJob.Status.PROGRESS, progress=25, step="Parsing")
    other = _job(org, status=SBOMJob.Status.PROGRESS, progress=80, step="Analysing")

    body = client.get(f"/history/row/{running.task_id}").content.decode()

    assert "Parsing" in body
    assert "Analysing" not in body
    assert 'hx-swap="outerHTML"' in body
    assert str(other.task_id) not in body


@pytest.mark.django_db
def test_the_partial_shows_phase_and_percentage(org_client) -> None:  # type: ignore[no-untyped-def]
    # Story 6.2: an in-progress row shows its phase and a progress bar, not just a badge.
    client, org = org_client
    job = _job(org, status=SBOMJob.Status.PROGRESS, progress=63, step="Scanning vulnerabilities")

    body = client.get(f"/history/row/{job.task_id}").content.decode()

    assert "Scanning vulnerabilities" in body
    assert "63" in body
    assert "In Progress" in body


@pytest.mark.django_db
def test_a_job_that_finishes_returns_a_row_without_a_trigger(org_client) -> None:  # type: ignore[no-untyped-def]
    """This is what makes polling self-terminate rather than needing client-side cancellation."""
    client, org = org_client
    job = _job(org, status=SBOMJob.Status.PROGRESS, progress=90, step="Finalising")

    assert EXPECTED_TRIGGER in client.get(f"/history/row/{job.task_id}").content.decode()

    SBOMJob.objects.filter(pk=job.pk).update(
        status=SBOMJob.Status.SUCCESS, completed_at=timezone.now(), result_key="sboms/x.json"
    )

    body = client.get(f"/history/row/{job.task_id}").content.decode()
    assert EXPECTED_TRIGGER not in body
    assert "Completed" in body


@pytest.mark.django_db
def test_a_failed_row_shows_its_failure_reason(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, status=SBOMJob.Status.FAILED, reason="unsupported_format")

    body = client.get(f"/history/row/{job.task_id}").content.decode()

    assert "Failed" in body
    assert "unsupported_format" in body
    assert EXPECTED_TRIGGER not in body


# --- AC #3: elapsed ticks, then freezes ---------------------------------------------------


@pytest.mark.django_db
def test_elapsed_advances_while_running_and_freezes_when_finished(org_client) -> None:  # type: ignore[no-untyped-def]
    """The freeze is a property of the data — a finished job measures to completed_at."""
    client, org = org_client
    job = _job(org, status=SBOMJob.Status.PROGRESS, progress=10)
    SBOMJob.objects.filter(pk=job.pk).update(created_at=timezone.now() - timedelta(seconds=90))

    running = client.get(f"/history/row/{job.task_id}").content.decode()
    assert "1m 3" in running  # ~1m30s and climbing

    completed_at = timezone.now()
    SBOMJob.objects.filter(pk=job.pk).update(status=SBOMJob.Status.SUCCESS, completed_at=completed_at)

    first = client.get(f"/history/row/{job.task_id}").content.decode()
    second = client.get(f"/history/row/{job.task_id}").content.decode()
    # Two reads a moment apart now agree, because the end point no longer moves.
    assert first == second


# --- AC #4: the results page gate ---------------------------------------------------------


@pytest.mark.django_db
def test_the_results_page_shows_progress_and_polls_while_running(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, status=SBOMJob.Status.PROGRESS, progress=55, step="Resolving")

    html = client.get(f"/results/{job.task_id}").content.decode()

    assert "Resolving" in html
    assert "55" in html
    assert EXPECTED_TRIGGER in html


@pytest.mark.django_db
def test_the_results_page_renders_the_completed_view_once_terminal(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, status=SBOMJob.Status.SUCCESS)

    html = client.get(f"/results/{job.task_id}").content.decode()

    # Story 21.12 replaced this story's placeholder with the five-tab shell; what 21.11 owns
    # is the transition itself, so the assertion is that the gate has opened onto the shell.
    assert "Overview" in html
    # No trigger, because there is nothing left to wait for.
    assert EXPECTED_TRIGGER not in html


@pytest.mark.django_db
def test_the_progress_fragment_asks_htmx_to_reload_once_the_job_is_done(org_client) -> None:  # type: ignore[no-untyped-def]
    """The transition is server-decided: the client does not have to notice terminality."""
    client, org = org_client
    job = _job(org, status=SBOMJob.Status.PROGRESS, progress=99)

    while_running = client.get(f"/results/{job.task_id}/progress")
    assert "HX-Refresh" not in while_running.headers

    SBOMJob.objects.filter(pk=job.pk).update(status=SBOMJob.Status.SUCCESS, completed_at=timezone.now())

    once_done = client.get(f"/results/{job.task_id}/progress")
    assert once_done.headers["HX-Refresh"] == "true"


@pytest.mark.django_db
def test_a_failed_job_shows_its_reason_on_the_results_page(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, status=SBOMJob.Status.FAILED, reason="timeout")

    html = client.get(f"/results/{job.task_id}").content.decode()

    assert "failed" in html.lower()
    assert "timeout" in html


# --- AC #5: errors stop, they do not spin -------------------------------------------------


@pytest.mark.django_db
def test_a_cross_org_job_is_indistinguishable_from_an_unknown_one(org_client) -> None:  # type: ignore[no-untyped-def]
    """AD-2: 404 for both, so polling cannot be used to discover that a job exists."""
    client, _ = org_client
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org, status=SBOMJob.Status.PROGRESS)
    unknown = "00000000-0000-0000-0000-000000000000"

    for url in (f"/history/row/{theirs.task_id}", f"/history/row/{unknown}"):
        assert client.get(url).status_code == 404

    for url in (f"/results/{theirs.task_id}", f"/results/{unknown}"):
        assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_the_progress_endpoint_is_org_scoped_too(org_client) -> None:  # type: ignore[no-untyped-def]
    client, _ = org_client
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org, status=SBOMJob.Status.PROGRESS)

    assert client.get(f"/results/{theirs.task_id}/progress").status_code == 404


@pytest.mark.django_db
def test_polling_endpoints_reject_post(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, status=SBOMJob.Status.PROGRESS)

    assert client.post(f"/history/row/{job.task_id}").status_code == 405
    assert client.post(f"/results/{job.task_id}/progress").status_code == 405


# --- The "one sanctioned poller" rule -----------------------------------------------------


def test_the_trigger_is_produced_in_exactly_one_place() -> None:
    """The SPA centralised polling in one hook so no component could add its own loop.

    The server-side equivalent: `poll_attrs` is the only producer of an hx-trigger, so a later
    tab story cannot quietly introduce a second polling convention.
    """
    from pathlib import Path

    app = Path(__file__).resolve().parents[2] / "src" / "django_apps" / "inventory"
    producers = [path.name for path in app.rglob("*.py") if "hx-trigger" in path.read_text(encoding="utf-8")]
    assert producers == ["tables.py"], producers
