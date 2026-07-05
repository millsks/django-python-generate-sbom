"""Tests for scheduled artifact expiry & cleanup (Story 7.1)."""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import override_settings
from django.utils import timezone

from generate_sbom.analysis.models import AnalysisReport
from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.services import delete_job_artifacts, finalize_job, purge_expired_artifacts
from generate_sbom.tasks.maintenance import purge_expired_artifacts as purge_task
from generate_sbom.users.models import Org, User
from generate_sbom.users.services import register_user

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _org() -> tuple[User, Org]:
    user = register_user(email=f"{uuid4().hex}@example.com", password="pw12345678")
    return user, user.org_memberships.select_related("org").get().org


def _blob(key: str) -> str:
    return default_storage.save(key, ContentFile(b"artifact-bytes"))


def _job(*, expires_at: object, with_artifacts: bool = True) -> SBOMJob:
    """Build a SUCCESS job with a manifest, a persisted SBOM blob and one report blob."""
    user, org = _org()
    upload = ManifestUpload(
        org=org,
        user=user,
        detected_format=ManifestUpload.Format.PIXI_LOCK,
        original_filename="pixi.lock",
        application_id="APP-1",
        component_name="web",
        repository_url="https://github.com/acme/web",
        source_branch="main",
    )
    upload.file.save("pixi.lock", ContentFile(b"version: 5\n"), save=False)
    upload.save()
    result_key = _blob(f"sbom-results/{uuid4().hex}/sbom.json") if with_artifacts else None
    job = SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        result_key=result_key,
        summary_stats={"total_packages": 3},
        completed_at=timezone.now(),
        artifacts_expire_at=expires_at,
    )
    if with_artifacts:
        AnalysisReport.objects.create(
            job=job,
            report_type=AnalysisReport.ReportType.VULN,
            artifact_key=_blob(f"reports/{uuid4().hex}/vuln.json"),
            summary={"vulnerable_package_count": 1},
        )
    return job


def test_retention_setting_drives_expiry_default_30_days() -> None:
    job = _job(expires_at=None, with_artifacts=False)
    SBOMJob.objects.filter(task_id=job.task_id).update(status=SBOMJob.Status.PROGRESS)

    finalize_job(str(job.task_id), "sbom-results/x/y/sbom.json", {"total_packages": 2})

    job.refresh_from_db()
    assert abs((job.artifacts_expire_at - job.completed_at) - timedelta(days=30)).total_seconds() < 5


@override_settings(ARTIFACT_RETENTION_DAYS=7)
def test_retention_is_env_overridable() -> None:
    job = _job(expires_at=None, with_artifacts=False)
    SBOMJob.objects.filter(task_id=job.task_id).update(status=SBOMJob.Status.PROGRESS)

    finalize_job(str(job.task_id), "sbom-results/x/y/sbom.json", {})

    job.refresh_from_db()
    assert abs((job.artifacts_expire_at - job.completed_at) - timedelta(days=7)).total_seconds() < 5


def test_delete_job_artifacts_removes_blobs_nulls_keys_and_keeps_metadata() -> None:
    job = _job(expires_at=timezone.now())
    report = job.reports.get()
    sbom_key, report_key = job.result_key, report.artifact_key
    assert default_storage.exists(sbom_key) and default_storage.exists(report_key)

    assert delete_job_artifacts(job) is True

    assert not default_storage.exists(sbom_key)
    assert not default_storage.exists(report_key)
    job.refresh_from_db()
    report.refresh_from_db()
    assert job.result_key is None
    assert report.artifact_key is None
    # The rows and their metadata are retained forever (FR-8.1).
    assert SBOMJob.objects.filter(task_id=job.task_id).exists()
    assert job.status == SBOMJob.Status.SUCCESS
    assert job.summary_stats == {"total_packages": 3}
    assert report.summary == {"vulnerable_package_count": 1}


def test_delete_is_idempotent_when_already_cleaned() -> None:
    job = _job(expires_at=timezone.now(), with_artifacts=False)  # result_key is None
    assert delete_job_artifacts(job) is False


def test_purge_cleans_only_expired_jobs_holding_artifacts() -> None:
    expired = _job(expires_at=timezone.now() - timedelta(days=1))
    future = _job(expires_at=timezone.now() + timedelta(days=10))
    already_cleaned = _job(expires_at=timezone.now() - timedelta(days=1), with_artifacts=False)
    future_key = future.result_key

    cleaned = purge_expired_artifacts()

    assert cleaned == 1  # only the expired job that still held artifacts
    expired.refresh_from_db()
    future.refresh_from_db()
    assert expired.result_key is None
    assert future.result_key == future_key and default_storage.exists(future_key)
    # Metadata for the already-cleaned job is untouched.
    assert SBOMJob.objects.filter(task_id=already_cleaned.task_id, result_key__isnull=True).exists()


def test_purge_respects_an_explicit_cutoff() -> None:
    job = _job(expires_at=timezone.now() + timedelta(days=5))

    # A cutoff past the job's expiry sweeps it even though "now" hasn't reached it.
    assert purge_expired_artifacts(now=timezone.now() + timedelta(days=6)) == 1
    job.refresh_from_db()
    assert job.result_key is None


def test_purge_task_delegates_to_the_service() -> None:
    with pytest.MonkeyPatch.context() as mp:
        called: dict[str, int] = {}

        def _fake() -> int:
            called["n"] = 4
            return 4

        mp.setattr("generate_sbom.tasks.maintenance.sbom_services.purge_expired_artifacts", _fake)
        result = purge_task.apply().get()

    assert result == 4
    assert called["n"] == 4
