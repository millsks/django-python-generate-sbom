"""Story 22.2: every Beat-scheduled task must exist in the Celery registry.

`app.conf.beat_schedule` names tasks by **string**. Nothing checked that those strings
resolve, so both entries pointed at a module Celery never imported: Beat dispatched them and
every worker answered `NotRegistered`. Artifact retention (FR-8.2) and the parselmouth
mapping refresh were silently dead.

Why the rest of the suite could not catch it: `tests/unit/test_maintenance_task.py` opens with
`from inventory.tasks.maintenance import refresh_parselmouth_mapping`, and that import
*registers the task for the test session*. Any test that reaches a task by importing its
module proves nothing about production. This module deliberately goes the other way round —
it asks the registry the same question Beat and the worker ask.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from config.celery_app import app
from inventory.analysis.models import AnalysisReport
from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.services import create_org, register_user

REFRESH = "inventory.tasks.maintenance.refresh_parselmouth_mapping"
PURGE = "inventory.tasks.maintenance.purge_expired_artifacts"


def _registry() -> set[str]:
    """Return the task names Celery knows about after normal discovery.

    ``app.tasks`` is lazy: without ``import_default_modules()`` it holds only Celery's own
    built-ins, and every assertion below would pass vacuously — including against the bug
    this module exists to catch.
    """
    app.loader.import_default_modules()
    return set(app.tasks)


def test_the_registry_is_actually_populated() -> None:
    """Guard the guard: if discovery silently stops working, the tests below mean nothing."""
    registry = _registry()

    project_tasks = {name for name in registry if name.startswith("inventory.")}
    assert len(project_tasks) >= 9, f"task discovery looks broken; found {sorted(project_tasks)}"


def test_every_scheduled_task_resolves_in_the_registry() -> None:
    """The assertion that was missing.

    Adding a `beat_schedule` entry without arranging for its module to be imported now fails
    here, naming the schedule entry — rather than failing at 03:00 in a worker log.
    """
    registry = _registry()

    missing = {
        entry_name: spec["task"] for entry_name, spec in app.conf.beat_schedule.items() if spec["task"] not in registry
    }

    assert not missing, (
        "these beat_schedule entries name tasks Celery never imported, so Beat will dispatch "
        f"them and every worker will raise NotRegistered: {missing}"
    )


def test_the_schedule_is_not_empty() -> None:
    # An empty schedule would make the test above pass while retention silently stopped.
    assert app.conf.beat_schedule, "beat_schedule is empty; scheduled maintenance is gone"


# --- AC #3: run them the way Beat dispatches them — by name, out of the registry ----------
#
# Every existing test for these two reaches them by importing the module, which is exactly
# what masked the bug. These resolve the callable from `app.tasks[...]` instead, so the test
# fails if registration regresses even though the import would still work.


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    """Keep artifact blobs in a temp dir rather than the repo's media/ tree."""
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _discovered() -> None:
    """Do what a worker does at boot: import the task modules before touching the registry.

    Without this, `app.tasks[PURGE]` raises `NotRegistered` — which is precisely the
    production symptom, and a useful reminder that a task is registered by *discovery*, not by
    existing on disk. Every lookup below therefore goes through the same path Beat's
    dispatch-by-name does.
    """
    app.loader.import_default_modules()


def _expired_job_with_artifacts() -> SBOMJob:
    """A SUCCESS job whose retention window has passed, holding an SBOM and a report blob."""
    user = register_user(email=f"{uuid4().hex}@example.com", password="pw12345678")
    org = create_org(name=uuid4().hex[:8], admin_user=user)
    upload = ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/t/requirements.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
    )
    job = SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        summary_stats={"total": 1},
        completed_at=timezone.now() - timedelta(days=40),
        artifacts_expire_at=timezone.now() - timedelta(days=10),
        result_key=default_storage.save("sboms/expired.json", ContentFile(b"sbom-bytes")),
    )
    AnalysisReport.objects.create(
        job=job,
        report_type=AnalysisReport.ReportType.VULN,
        artifact_key=default_storage.save("reports/expired.json", ContentFile(b"report-bytes")),
        summary={},
    )
    return job


@pytest.mark.django_db
def test_the_purge_task_runs_from_the_registry_and_clears_the_artifacts() -> None:
    """FR-8.2: expired blobs go. FR-8.1: the job record and its metadata stay."""
    job = _expired_job_with_artifacts()
    sbom_key = job.result_key
    report = job.reports.first()
    report_key = report.artifact_key
    assert default_storage.exists(sbom_key)

    cleaned = app.tasks[PURGE].apply().get()

    assert cleaned == 1
    # The blobs are gone and the keys are nulled (AD-6: blobs live only in storage).
    assert not default_storage.exists(sbom_key)
    assert not default_storage.exists(report_key)
    job.refresh_from_db()
    report.refresh_from_db()
    assert job.result_key is None
    assert report.artifact_key is None
    # ...and the record survives, which is the half a too-eager sweep would get wrong.
    assert SBOMJob.objects.filter(pk=job.pk).exists()
    assert job.status == SBOMJob.Status.SUCCESS
    assert job.summary_stats == {"total": 1}


@pytest.mark.django_db
def test_the_purge_task_leaves_unexpired_jobs_alone() -> None:
    """The inverse assertion: a sweep that deletes everything would pass the test above."""
    job = _expired_job_with_artifacts()
    job.artifacts_expire_at = timezone.now() + timedelta(days=5)
    job.save(update_fields=["artifacts_expire_at"])

    assert app.tasks[PURGE].apply().get() == 0

    job.refresh_from_db()
    assert job.result_key is not None


def test_the_refresh_task_runs_from_the_registry() -> None:
    """Mapping refresh reaches the parselmouth service; the HTTP call itself is mocked."""
    with patch("inventory.tasks.maintenance.parselmouth.refresh_mapping", return_value=7) as refresh:
        result = app.tasks[REFRESH].apply().get()

    refresh.assert_called_once()
    assert result == 7
