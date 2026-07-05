"""Tests for job submission, the concurrency gate, and status polling (Story 3.2)."""

from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.services import finalize_job, update_job_status
from generate_sbom.users.services import register_user

_DISPATCH = "generate_sbom.sbom.views.run_sbom_pipeline.delay_on_commit"
META = {
    "application_id": "APP-1",
    "component_name": "web",
    "repository_url": "https://github.com/acme/web",
    "source_branch": "main",
}


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _login(email: str = "alice@example.com") -> APIClient:
    register_user(email=email, password="pw12345678")
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": "pw12345678"}, format="json")
    return client


def _generate(client: APIClient, content: bytes = b"django==5.2\n", **overrides: str) -> object:
    file = SimpleUploadedFile("requirements.txt", content, content_type="text/plain")
    return client.post(
        "/api/v1/sbom/generate/",
        {"file": file, **META, **overrides},
        format="multipart",
    )


@pytest.mark.django_db
def test_generate_creates_pending_job_and_dispatches() -> None:
    client = _login()
    with patch(_DISPATCH) as dispatch:
        response = _generate(client)

    assert response.status_code == 202
    assert response.data["status"] == "PENDING"
    assert response.data["estimated_seconds"] >= 0
    job = SBOMJob.objects.get(task_id=response.data["task_id"])
    assert job.status == SBOMJob.Status.PENDING
    assert job.output_format == "cyclonedx-json"  # cdx-json default
    dispatch.assert_called_once_with(str(job.task_id))


@pytest.mark.django_db
def test_output_format_is_mapped_and_validated() -> None:
    client = _login()
    with patch(_DISPATCH):
        ok = _generate(client, output_format="spdx-2.3")
        bad = _generate(client, content=b"flask==3.0\n", output_format="xml")

    assert ok.status_code == 202
    assert SBOMJob.objects.get(task_id=ok.data["task_id"]).output_format == "spdx-json"
    assert bad.status_code == 400
    assert bad.data["code"] == "validation_error"


@pytest.mark.django_db
def test_concurrency_gate_returns_429(settings: pytest.FixtureRequest) -> None:
    settings.SBOM_MAX_CONCURRENT_JOBS_PER_ORG = 1  # type: ignore[attr-defined]
    client = _login()
    with patch(_DISPATCH):
        _generate(client)  # one PENDING job
        response = _generate(client, content=b"flask==3.0\n")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert response.data["code"] == "rate_limited"


@pytest.mark.django_db
def test_status_poll_returns_shape_and_reflects_updates() -> None:
    client = _login()
    with patch(_DISPATCH):
        task_id = _generate(client).data["task_id"]

    initial = client.get(f"/api/v1/sbom/status/{task_id}/")
    assert initial.status_code == 200
    assert initial.data["status"] == "PENDING"
    assert initial.data["progress"] == 0
    assert initial.data["result_url"] is None

    update_job_status(task_id, SBOMJob.Status.PROGRESS, progress=42, current_step="vulnerability scan")
    progressing = client.get(f"/api/v1/sbom/status/{task_id}/")
    assert progressing.data["status"] == "PROGRESS"
    assert progressing.data["progress"] == 42
    assert progressing.data["current_phase"] == "vulnerability scan"

    finalize_job(task_id, "sbom-results/x/y/sbom.json", {"total_packages": 2})
    done = client.get(f"/api/v1/sbom/status/{task_id}/")
    assert done.data["status"] == "SUCCESS"
    assert done.data["result_url"] is not None
    assert done.data["artifacts_available"] is True
    assert done.data["artifacts_expire_at"] is not None  # finalize sets the retention window

    # Once artifacts are cleaned (expiry sweep / manual delete) result_key is nulled: the
    # status still reports SUCCESS + retained metadata, but advertises no download (Story 7.3).
    job = SBOMJob.objects.get(task_id=task_id)
    job.result_key = None
    job.save(update_fields=["result_key"])
    expired = client.get(f"/api/v1/sbom/status/{task_id}/")
    assert expired.data["status"] == "SUCCESS"
    assert expired.data["artifacts_available"] is False
    assert expired.data["result_url"] is None
    assert expired.data["summary_stats"]["total_packages"] == 2  # metadata retained


@pytest.mark.django_db
def test_cross_org_status_poll_returns_404() -> None:
    alice = _login("alice@example.com")
    with patch(_DISPATCH):
        task_id = _generate(alice).data["task_id"]
    bob = _login("bob@example.com")

    response = bob.get(f"/api/v1/sbom/status/{task_id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_generate_via_api_key_creates_userless_job() -> None:
    # Programmatic (API-key) requests have an org but no user; the job and its
    # manifest must persist with user=None rather than 500 on a NOT NULL violation.
    admin = _login("alice@example.com")  # helper registers + logs in
    key = admin.post("/api/v1/keys/", {"name": "ci"}, format="json").data["key"]

    file = SimpleUploadedFile("pixi.lock", b"version: 5\npackages: []\n", content_type="text/plain")
    with patch(_DISPATCH):
        response = APIClient().post(
            "/api/v1/sbom/generate/",
            {"file": file, **META},
            format="multipart",
            HTTP_AUTHORIZATION=f"Api-Key {key}",
        )

    assert response.status_code == 202
    job = SBOMJob.objects.select_related("manifest").get(task_id=response.data["task_id"])
    assert job.user is None
    assert job.manifest.user is None


@pytest.mark.django_db
def test_generate_requires_authentication() -> None:
    file = SimpleUploadedFile("requirements.txt", b"django==5.2\n")
    response = APIClient().post("/api/v1/sbom/generate/", {"file": file, **META}, format="multipart")
    assert response.status_code in (401, 403)
