"""Tests for the jobs-list selector and endpoint (Story 6.1)."""

from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from rest_framework.test import APIClient

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.selectors import get_jobs
from generate_sbom.sbom.serializers import JobListSerializer
from generate_sbom.users.models import Org, User
from generate_sbom.users.services import register_user


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _org(email: str) -> tuple[User, Org]:
    user = register_user(email=email, password="pw12345678")
    return user, user.org_memberships.select_related("org").get().org


def _job(org: Org, user: User, *, fmt: str = "pixi_lock", status: str = "SUCCESS") -> SBOMJob:
    upload = ManifestUpload(
        org=org,
        user=user,
        detected_format=fmt,
        original_filename=f"{fmt}.file",
        application_id="A",
        component_name="c",
        repository_url="https://github.com/a/b",
        source_branch="main",
    )
    upload.file.save("m", ContentFile(b"x"), save=False)
    upload.save()
    return SBOMJob.objects.create(org=org, manifest=upload, output_format="cyclonedx-json", status=status)


def _login(email: str) -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": "pw12345678"}, format="json")
    return client


@pytest.mark.django_db
def test_selector_returns_only_org_jobs_most_recent_first() -> None:
    alice, alice_org = _org("alice@example.com")
    bob, bob_org = _org("bob@example.com")
    first = _job(alice_org, alice)
    second = _job(alice_org, alice)
    _job(bob_org, bob)  # other org — excluded

    jobs = list(get_jobs(alice_org))

    assert [j.task_id for j in jobs] == [second.task_id, first.task_id]  # most-recent-first


@pytest.mark.django_db
def test_selector_status_and_format_filters() -> None:
    alice, org = _org("alice@example.com")
    _job(org, alice, status="SUCCESS", fmt="pixi_lock")
    _job(org, alice, status="PROGRESS", fmt="requirements")
    _job(org, alice, status="FAILED", fmt="conda")

    assert get_jobs(org, status_filter="Completed").count() == 1
    assert get_jobs(org, status_filter="In Progress").count() == 1
    assert get_jobs(org, status_filter="Failed").count() == 1
    assert get_jobs(org, status_filter="All").count() == 3
    assert get_jobs(org, format_filter="conda").count() == 1
    assert get_jobs(org, status_filter="Completed", format_filter="requirements").count() == 0


@pytest.mark.django_db
def test_endpoint_paginates_and_serializes() -> None:
    alice, org = _org("alice@example.com")
    job = _job(org, alice, fmt="requirements")

    response = _login("alice@example.com").get("/api/v1/sbom/jobs/")

    assert response.status_code == 200
    assert set(response.data) == {"count", "next", "previous", "results"}
    assert response.data["count"] == 1
    row = response.data["results"][0]
    assert row["task_id"] == str(job.task_id)
    assert row["manifest_filename"] == "requirements.file"
    assert row["manifest_format"] == "requirements"
    assert row["output_format"] == "cyclonedx-json"
    assert row["status"] == "SUCCESS"
    assert row["elapsed_seconds"] is None  # no completion timestamp yet


@pytest.mark.django_db
def test_serializer_elapsed_seconds_for_completed_and_running_jobs() -> None:
    alice, org = _org("alice@example.com")
    done = _job(org, alice, status="SUCCESS")
    done.completed_at = done.created_at + timedelta(seconds=90)
    done.save(update_fields=["completed_at"])
    running = _job(org, alice, status="PROGRESS")  # completed_at is None

    assert JobListSerializer(done).data["elapsed_seconds"] == 90.0
    assert JobListSerializer(running).data["elapsed_seconds"] is None


@pytest.mark.django_db
def test_serializer_artifacts_available_reflects_result_key() -> None:
    alice, org = _org("alice@example.com")
    stored = _job(org, alice, status="SUCCESS")
    stored.result_key = "sbom/stored.json"
    stored.save(update_fields=["result_key"])
    cleaned = _job(org, alice, status="SUCCESS")  # result_key null -> artifacts expired/deleted

    assert JobListSerializer(stored).data["artifacts_available"] is True
    assert JobListSerializer(cleaned).data["artifacts_available"] is False
    # The retained expiry timestamp is exposed for the UI to show.
    assert "artifacts_expire_at" in JobListSerializer(cleaned).data


@pytest.mark.django_db
def test_endpoint_page_size_25() -> None:
    alice, org = _org("alice@example.com")
    for _ in range(30):
        _job(org, alice)

    response = _login("alice@example.com").get("/api/v1/sbom/jobs/")

    assert response.data["count"] == 30
    assert len(response.data["results"]) == 25  # default page size
    assert response.data["next"] is not None


@pytest.mark.django_db
def test_endpoint_excludes_other_orgs() -> None:
    _org("alice@example.com")  # register alice so login works
    bob, bob_org = _org("bob@example.com")
    _job(bob_org, bob)

    response = _login("alice@example.com").get("/api/v1/sbom/jobs/")

    assert response.data["count"] == 0


@pytest.mark.django_db
def test_endpoint_status_filter_param() -> None:
    alice, org = _org("alice@example.com")
    _job(org, alice, status="SUCCESS")
    _job(org, alice, status="FAILED")

    response = _login("alice@example.com").get("/api/v1/sbom/jobs/?status=Failed")

    assert response.data["count"] == 1
    assert response.data["results"][0]["status"] == "FAILED"
