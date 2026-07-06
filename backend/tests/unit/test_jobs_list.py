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
from generate_sbom.users.services import create_org, register_user


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _org(email: str) -> tuple[User, Org]:
    user = register_user(email=email, password="pw12345678")
    return user, create_org(name=user.email.split("@")[0], admin_user=user)


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


@pytest.mark.django_db
@pytest.mark.parametrize("fmt", list(ManifestUpload.Format.values))
def test_endpoint_format_filter_matches_every_canonical_format(fmt: str) -> None:
    """Every canonical format (incl. pixi_toml) returns 200 with only its matching job (AC #1)."""
    alice, org = _org("alice@example.com")
    match = _job(org, alice, fmt=fmt)
    other = next(f for f in ManifestUpload.Format.values if f != fmt)
    _job(org, alice, fmt=other)  # different format — must be excluded

    response = _login("alice@example.com").get(f"/api/v1/sbom/jobs/?format={fmt}")

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["task_id"] == str(match.task_id)
    assert response.data["results"][0]["manifest_format"] == fmt


@pytest.mark.django_db
def test_endpoint_format_filter_all_returns_every_format() -> None:
    """No format param (the 'All' selection) returns jobs of every format (AC #2, no regression)."""
    alice, org = _org("alice@example.com")
    for fmt in ManifestUpload.Format.values:
        _job(org, alice, fmt=fmt)

    response = _login("alice@example.com").get("/api/v1/sbom/jobs/")

    assert response.status_code == 200
    assert response.data["count"] == len(ManifestUpload.Format.values)


@pytest.mark.django_db
def test_endpoint_invalid_format_degrades_to_empty_not_error() -> None:
    """An unknown format degrades to an empty 200, never a 400/500 (AC #3)."""
    alice, org = _org("alice@example.com")
    _job(org, alice, fmt="pixi_toml")

    response = _login("alice@example.com").get("/api/v1/sbom/jobs/?format=not_a_real_format")

    assert response.status_code == 200
    assert response.data["count"] == 0


@pytest.mark.django_db
def test_selector_invalid_format_returns_empty_queryset() -> None:
    """The selector ignores nothing and raises nothing for a bad format — it returns empty (AC #3)."""
    alice, org = _org("alice@example.com")
    _job(org, alice, fmt="pixi_toml")

    assert get_jobs(org, format_filter="bogus").count() == 0
    assert get_jobs(org, format_filter="pixi_toml").count() == 1
