"""Whole-record deletion — the service behind Job Status's delete buttons.

Distinct from `test_artifact_deletion.py`, which covers the artifact-only purge the API still
offers and which keeps every record (FR-8.1). This one deletes the record: job, tasks,
reports, manifest, and every blob any of them owns. It is the one place in the app where job
history is destroyed, so the tests are about what is left behind — in the database and in
storage.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from django_service.users.models import User
from inventory.analysis.models import AnalysisReport
from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import JobTask, SBOMJob
from inventory.sbom.services import create_job, delete_job_record, delete_job_records
from inventory.users.models import Org
from inventory.users.services import create_org, register_user

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


@pytest.fixture
def org_user() -> tuple[Org, User]:
    user = register_user(email="dev@example.com", password="pw12345678")
    return create_org(name="Acme", admin_user=user), user


def _manifest(org: Org, user: User) -> ManifestUpload:
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
    return upload


def _job(org: Org, user: User, manifest: ManifestUpload | None = None) -> SBOMJob:
    """A SUCCESS job with a stored SBOM blob and one report blob."""
    job = create_job(org, manifest or _manifest(org, user), user, "cyclonedx-json")
    SBOMJob.objects.filter(pk=job.pk).update(
        status=SBOMJob.Status.SUCCESS,
        result_key=default_storage.save(f"sbom-results/{uuid4().hex}/sbom.json", ContentFile(b"{}")),
    )
    job.refresh_from_db()
    AnalysisReport.objects.create(
        job=job,
        report_type=AnalysisReport.ReportType.VULN,
        artifact_key=default_storage.save(f"reports/{uuid4().hex}/vuln.json", ContentFile(b"{}")),
        summary={"vulnerable_package_count": 1},
    )
    return job


def test_the_record_and_every_blob_it_owns_are_gone(org_user: tuple[Org, User]) -> None:
    org, user = org_user
    job = _job(org, user)
    blobs = [job.result_key, job.reports.get().artifact_key, job.manifest.file.name]
    assert all(default_storage.exists(key) for key in blobs)

    delete_job_record(job)

    assert not SBOMJob.objects.filter(pk=job.pk).exists()
    assert not AnalysisReport.objects.filter(job_id=job.pk).exists()
    assert not JobTask.objects.filter(job_id=job.pk).exists()
    assert not ManifestUpload.objects.exists()
    for key in blobs:
        assert not default_storage.exists(key), key


def test_a_manifest_shared_with_another_job_survives(org_user: tuple[Org, User]) -> None:
    """Deleting one re-run must not pull the upload out from under the job that still needs it."""
    org, user = org_user
    manifest = _manifest(org, user)
    first, second = _job(org, user, manifest), _job(org, user, manifest)

    delete_job_record(first)

    assert SBOMJob.objects.filter(pk=second.pk).exists()
    assert ManifestUpload.objects.filter(pk=manifest.pk).exists()
    assert default_storage.exists(manifest.file.name)


def test_deleting_the_last_job_takes_the_shared_manifest_with_it(org_user: tuple[Org, User]) -> None:
    org, user = org_user
    manifest = _manifest(org, user)
    first, second = _job(org, user, manifest), _job(org, user, manifest)
    manifest_file = manifest.file.name

    delete_job_record(first)
    delete_job_record(second)

    assert not ManifestUpload.objects.filter(pk=manifest.pk).exists()
    assert not default_storage.exists(manifest_file)


def test_a_job_with_no_blobs_left_still_deletes(org_user: tuple[Org, User]) -> None:
    """Artifacts purged under retention (Story 7.3) leave a record that must still be deletable."""
    org, user = org_user
    job = _job(org, user)
    SBOMJob.objects.filter(pk=job.pk).update(result_key=None)
    job.reports.update(artifact_key=None)
    job.refresh_from_db()

    delete_job_record(job)

    assert not SBOMJob.objects.filter(pk=job.pk).exists()


def test_the_bulk_helper_counts_what_it_deleted(org_user: tuple[Org, User]) -> None:
    org, user = org_user
    jobs = [_job(org, user) for _ in range(3)]

    deleted = delete_job_records(SBOMJob.objects.filter(pk__in=[job.pk for job in jobs]))

    assert deleted == 3
    assert not SBOMJob.objects.exists()


def test_another_orgs_records_are_untouched(org_user: tuple[Org, User]) -> None:
    org, user = org_user
    mine = _job(org, user)
    outsider = register_user(email="outsider@example.com", password="pw12345678")
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org, outsider)

    delete_job_records(SBOMJob.objects.filter(pk=mine.pk))

    assert SBOMJob.objects.filter(pk=theirs.pk).exists()
    assert default_storage.exists(theirs.result_key or "")
