"""Story 22.6: expired-artifact purging is manual and reviewable, not scheduled.

The nightly Beat sweep is gone (product-owner direction). What replaces it is a management
command with a `--dry-run` mode, so an operator sees what would be deleted before deleting it.

The load-bearing assertions here are the two that would let the old behaviour creep back: that
no schedule entry purges anything, and that `--dry-run` deletes **nothing**. A dry run that
quietly deleted would be the worst possible failure of this feature, since its whole purpose is
to be safe to run.
"""

from __future__ import annotations

from datetime import timedelta
from io import StringIO
from uuid import uuid4

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.utils import timezone

from config.celery_app import app
from inventory.analysis.models import AnalysisReport
from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.services import create_org, register_user

COMMAND = "purge_expired_artifacts"


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _job(*, expired: bool, with_report: bool = True) -> SBOMJob:
    """A SUCCESS job holding an SBOM blob, expired or not."""
    user = register_user(email=f"{uuid4().hex}@example.com", password="pw12345678")
    org = create_org(name=uuid4().hex[:8], admin_user=user)
    upload = ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/t/requirements.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
    )
    offset = timedelta(days=-10) if expired else timedelta(days=10)
    job = SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        summary_stats={"total": 3},
        completed_at=timezone.now() - timedelta(days=40),
        artifacts_expire_at=timezone.now() + offset,
        result_key=default_storage.save(f"sboms/{uuid4().hex}.json", ContentFile(b"sbom-bytes")),
    )
    if with_report:
        AnalysisReport.objects.create(
            job=job,
            report_type=AnalysisReport.ReportType.VULN,
            artifact_key=default_storage.save(f"reports/{uuid4().hex}.json", ContentFile(b"report-bytes")),
            summary={},
        )
    return job


def _run(*args: str) -> str:
    out = StringIO()
    call_command(COMMAND, *args, stdout=out)
    return out.getvalue()


# --- AC #1: nothing purges on a schedule -------------------------------------------------


def test_no_beat_entry_purges_artifacts() -> None:
    """Asserted against the schedule rather than the diff, so a re-add fails here."""
    scheduled = {spec["task"] for spec in app.conf.beat_schedule.values()}

    assert "inventory.tasks.maintenance.purge_expired_artifacts" not in scheduled
    assert not any("purge" in name for name in app.conf.beat_schedule), app.conf.beat_schedule


def test_the_mapping_refresh_is_still_scheduled() -> None:
    """The other entry must survive — this story removes one job, not the schedule."""
    scheduled = {spec["task"] for spec in app.conf.beat_schedule.values()}

    assert "inventory.tasks.maintenance.refresh_parselmouth_mapping" in scheduled


def test_the_purge_task_is_still_registered_for_manual_dispatch() -> None:
    """Unscheduled is not the same as unavailable: it can still be sent to a worker."""
    app.loader.import_default_modules()

    assert "inventory.tasks.maintenance.purge_expired_artifacts" in app.tasks


# --- AC #3: the dry run reviews without deleting ------------------------------------------


@pytest.mark.django_db
def test_dry_run_reports_the_expired_jobs_and_deletes_nothing() -> None:
    """The whole point of the flag. If this ever fails, the feature is actively dangerous."""
    job = _job(expired=True)
    key = job.result_key
    report_key = job.reports.first().artifact_key

    output = _run("--dry-run")

    assert str(job.task_id) in output
    assert "nothing was deleted" in output
    # Nothing touched: blobs present, keys intact.
    assert default_storage.exists(key)
    assert default_storage.exists(report_key)
    job.refresh_from_db()
    assert job.result_key == key


@pytest.mark.django_db
def test_dry_run_reports_the_report_count_so_the_scale_is_visible() -> None:
    job = _job(expired=True)

    output = _run("--dry-run")

    assert f"org={job.org.slug}" in output
    assert "sbom=1 reports=1" in output


@pytest.mark.django_db
def test_dry_run_says_so_plainly_when_there_is_nothing_to_do() -> None:
    _job(expired=False)

    assert "No expired artifacts to purge." in _run("--dry-run")


# --- AC #4: the real run matches what the schedule used to do ------------------------------


@pytest.mark.django_db
def test_the_command_purges_expired_blobs_and_keeps_the_job_record() -> None:
    """FR-8.2's deletion, FR-8.1's retention — the same pair the Beat task guaranteed."""
    job = _job(expired=True)
    key = job.result_key
    report = job.reports.first()
    report_key = report.artifact_key

    output = _run()

    assert not default_storage.exists(key)
    assert not default_storage.exists(report_key)
    job.refresh_from_db()
    report.refresh_from_db()
    assert job.result_key is None
    assert report.artifact_key is None
    # Retained: the record, its status, and its metadata.
    assert SBOMJob.objects.filter(pk=job.pk).exists()
    assert job.status == SBOMJob.Status.SUCCESS
    assert job.summary_stats == {"total": 3}
    assert "1 job(s)" in output


@pytest.mark.django_db
def test_the_command_leaves_unexpired_jobs_alone() -> None:
    """The inverse assertion: a sweep that purged everything would pass the test above."""
    expired = _job(expired=True)
    live = _job(expired=False)
    live_key = live.result_key

    _run()

    expired.refresh_from_db()
    live.refresh_from_db()
    assert expired.result_key is None
    assert live.result_key == live_key
    assert default_storage.exists(live_key)


@pytest.mark.django_db
def test_the_command_sweeps_across_orgs() -> None:
    """Deliberately not org-scoped: this is a system sweep, not a request (no acting org)."""
    first = _job(expired=True)
    second = _job(expired=True)
    assert first.org_id != second.org_id

    output = _run()

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.result_key is None
    assert second.result_key is None
    assert "2 job(s)" in output


@pytest.mark.django_db
def test_running_twice_is_idempotent() -> None:
    """A second run must find nothing rather than error on already-deleted blobs."""
    _job(expired=True)
    _run()

    assert "No expired artifacts to purge." in _run()


@pytest.mark.django_db
def test_a_job_with_no_artifacts_is_not_reported_as_purgeable() -> None:
    """`result_key IS NOT NULL` is half the selection rule; without it the count would lie."""
    job = _job(expired=True)
    job.result_key = None
    job.save(update_fields=["result_key"])

    assert "No expired artifacts to purge." in _run("--dry-run")
