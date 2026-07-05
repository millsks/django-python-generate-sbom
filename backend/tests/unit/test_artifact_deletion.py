"""Tests for on-demand manual & bulk artifact deletion (Story 7.2)."""

from uuid import uuid4

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from generate_sbom.analysis.models import AnalysisReport
from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.users.models import Org, OrgMembership, User
from generate_sbom.users.services import create_org, register_user

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _setup(email: str) -> tuple[APIClient, User, Org]:
    """Register (admin of a fresh org) + log in; return the client, user, and org."""
    user = register_user(email=email, password="pw12345678")
    org = create_org(name=user.email.split("@")[0], admin_user=user)
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": "pw12345678"}, format="json")
    return client, user, org


def _job(org: Org, user: User, *, with_artifacts: bool = True) -> SBOMJob:
    """A SUCCESS job with a manifest, a persisted SBOM blob, and one report blob."""
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
    result_key = (
        default_storage.save(f"sbom-results/{uuid4().hex}/sbom.json", ContentFile(b"{}")) if with_artifacts else None
    )
    job = SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        result_key=result_key,
        summary_stats={"total_packages": 3},
    )
    if with_artifacts:
        AnalysisReport.objects.create(
            job=job,
            report_type=AnalysisReport.ReportType.VULN,
            artifact_key=default_storage.save(f"reports/{uuid4().hex}/vuln.json", ContentFile(b"{}")),
            summary={"vulnerable_package_count": 1},
        )
    return job


def test_delete_single_purges_blobs_and_retains_record() -> None:
    client, user, org = _setup("alice@example.com")
    job = _job(org, user)
    report = job.reports.get()
    result_blob, report_blob = job.result_key, report.artifact_key
    assert default_storage.exists(result_blob)
    assert default_storage.exists(report_blob)

    response = client.delete(f"/api/v1/sbom/jobs/{job.task_id}/artifacts/")

    assert response.status_code == 200
    assert response.data == {"task_id": str(job.task_id), "deleted": True}
    job.refresh_from_db()
    report.refresh_from_db()
    # Keys nulled and blobs gone; the record + its metadata are retained forever.
    assert job.result_key is None
    assert report.artifact_key is None
    assert not default_storage.exists(result_blob)
    assert not default_storage.exists(report_blob)
    assert SBOMJob.objects.filter(task_id=job.task_id).exists()
    assert job.summary_stats == {"total_packages": 3}


def test_delete_cross_org_returns_404() -> None:
    _, alice, alice_org = _setup("alice@example.com")
    job = _job(alice_org, alice)
    bob_client, _, _ = _setup("bob@example.com")

    response = bob_client.delete(f"/api/v1/sbom/jobs/{job.task_id}/artifacts/")

    assert response.status_code == 404
    job.refresh_from_db()
    assert job.result_key is not None  # untouched


def test_delete_is_idempotent() -> None:
    client, user, org = _setup("alice@example.com")
    job = _job(org, user)

    first = client.delete(f"/api/v1/sbom/jobs/{job.task_id}/artifacts/")
    second = client.delete(f"/api/v1/sbom/jobs/{job.task_id}/artifacts/")

    assert first.status_code == 200 and first.data["deleted"] is True
    assert second.status_code == 200 and second.data["deleted"] is False


def test_bulk_delete_by_task_ids() -> None:
    client, user, org = _setup("alice@example.com")
    a, b = _job(org, user), _job(org, user)
    keep = _job(org, user)

    response = client.post(
        "/api/v1/sbom/jobs/artifacts/bulk-delete/",
        {"task_ids": [str(a.task_id), str(b.task_id)]},
        format="json",
    )

    assert response.status_code == 200
    assert response.data == {"deleted": 2, "requested": 2}
    for job in (a, b):
        job.refresh_from_db()
        assert job.result_key is None
    keep.refresh_from_db()
    assert keep.result_key is not None


def test_bulk_delete_all_org_as_admin() -> None:
    client, user, org = _setup("alice@example.com")
    jobs = [_job(org, user) for _ in range(3)]

    response = client.post("/api/v1/sbom/jobs/artifacts/bulk-delete/", {"all": True}, format="json")

    assert response.status_code == 200
    assert response.data["deleted"] == 3
    for job in jobs:
        job.refresh_from_db()
        assert job.result_key is None


def test_bulk_delete_all_org_forbidden_for_member() -> None:
    client, user, org = _setup("member@example.com")
    job = _job(org, user)
    # Downgrade the caller to a non-admin member of their active org.
    OrgMembership.objects.filter(user=user, org=org).update(role=OrgMembership.Role.MEMBER)

    response = client.post("/api/v1/sbom/jobs/artifacts/bulk-delete/", {"all": True}, format="json")

    assert response.status_code == 403
    assert response.data["code"] == "forbidden"
    job.refresh_from_db()
    assert job.result_key is not None  # untouched
