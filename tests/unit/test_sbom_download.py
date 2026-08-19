"""The results page's Download SBOM button.

The button linked straight at `/api/v1/sbom/result/{id}/`, which is org-scoped (AD-8). Story
22.16 made the results page cross-org, so on another org's job the page rendered and the
button answered `{"error": "Job not found."}`. These pin the fix: the button goes through the
page's own route, which scopes the way the page does.
"""

from __future__ import annotations

from unittest import mock

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org
from inventory.users.services import create_org, register_user

PASSWORD = "pw12345678"


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


def _job(org: Org, *, status: str = SBOMJob.Status.SUCCESS, purged: bool = False) -> SBOMJob:
    upload = ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
        application_id="APP-1",
        component_name="billing",
        repository_url="https://example.com/r",
        source_branch="main",
    )
    result_key = None
    if not purged and status == SBOMJob.Status.SUCCESS:
        result_key = f"sboms/{upload.pk}.json"
        default_storage.save(result_key, ContentFile(b'{"bomFormat": "CycloneDX"}'))
    return SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=status,
        result_key=result_key,
        summary_stats={"total_packages": 1},
    )


@pytest.fixture
def org_client():  # type: ignore[no-untyped-def]
    user = register_user(email="dev@example.com", password=PASSWORD)
    org = create_org(name="Acme", admin_user=user)
    return _client("dev@example.com"), org


@pytest.mark.django_db
def test_the_button_points_at_the_pages_route_not_the_scoped_api(org_client) -> None:  # type: ignore[no-untyped-def]
    """Both places the button appears: the Overview, and the raw view's too-large notice."""
    client, org = org_client
    job = _job(org)

    overview = client.get(f"/results/{job.task_id}").content.decode()
    assert f"/results/{job.task_id}/sbom/download" in overview
    assert "/api/v1/sbom/result/" not in overview

    # The raw view only offers the download when the document is too big to inline.
    with mock.patch("inventory.sbom.pages.RAW_INLINE_MAX_BYTES", 0):
        raw = client.get(f"/results/{job.task_id}/sbom/raw").content.decode()
    assert f"/results/{job.task_id}/sbom/download" in raw
    assert "/api/v1/sbom/result/" not in raw


@pytest.mark.django_db
def test_downloading_redirects_to_the_stored_artifact(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    response = client.get(f"/results/{job.task_id}/sbom/download")

    assert response.status_code == 302
    assert job.result_key is not None
    assert job.result_key in response["Location"]


@pytest.mark.django_db
def test_another_orgs_sbom_downloads_rather_than_404ing(org_client) -> None:  # type: ignore[no-untyped-def]
    """The bug: the page opened, the button did not."""
    client, _ = org_client
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org)

    response = client.get(f"/results/{theirs.task_id}/sbom/download")

    assert response.status_code == 302


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("status", "purged"),
    [
        (SBOMJob.Status.SUCCESS, True),  # artifacts purged under retention (Story 7.3)
        (SBOMJob.Status.PROGRESS, False),  # nothing generated yet
        (SBOMJob.Status.FAILED, False),
    ],
)
def test_a_job_with_nothing_to_serve_is_404(org_client, status: str, purged: bool) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, status=status, purged=purged)

    assert client.get(f"/results/{job.task_id}/sbom/download").status_code == 404


@pytest.mark.django_db
def test_an_unknown_job_is_404(org_client) -> None:  # type: ignore[no-untyped-def]
    client, _ = org_client
    assert client.get("/results/00000000-0000-0000-0000-000000000000/sbom/download").status_code == 404
