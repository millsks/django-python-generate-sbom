"""Integration: generate → persist → download round trip against real storage (Story 3.4).

Dev/test storage is the filesystem (FileSystemStorage → MEDIA_ROOT); the code path
is identical for MinIO/S3 in production (AD-6/AD-11). Real blob write and read-back,
no mocked infrastructure.
"""

import json
from dataclasses import asdict
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.parsers import PackageSpec
from generate_sbom.tasks.sbom_pipeline import generate_sbom_document as generate_phase
from generate_sbom.tasks.sbom_pipeline import persist_artifacts
from generate_sbom.users.services import register_user

PKGS = [PackageSpec(name="django", version="5.2.1"), PackageSpec(name="asgiref", version="3.8.1")]
_NO_UPDATE = "celery.app.task.Task.update_state"


def _make_job(output_format: str) -> SBOMJob:
    user = register_user(email="alice@example.com", password="pw12345678")
    org = user.org_memberships.select_related("org").get().org
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
    return SBOMJob.objects.create(org=org, manifest=upload, output_format=output_format)


@pytest.mark.integration
@pytest.mark.django_db
def test_generate_persist_download_roundtrip(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]
    job = _make_job("spdx-json")
    prev = {"task_id": str(job.task_id), "packages": [asdict(pkg) for pkg in PKGS]}

    with patch(_NO_UPDATE):
        generate_phase.apply(args=(prev,)).get()  # writes the blob + records the key
        persist_artifacts.apply(args=(str(job.task_id),)).get()

    job.refresh_from_db()
    assert job.status == SBOMJob.Status.SUCCESS
    assert job.summary_stats == {"total_packages": 2}

    # Real read-back from storage — the blob actually landed on disk.
    with default_storage.open(job.result_key) as handle:
        document = json.loads(handle.read())
    assert document["spdxVersion"] == "SPDX-2.3"

    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": "pw12345678"}, format="json")
    response = client.get(f"/api/v1/sbom/result/{job.task_id}/")
    assert response.status_code == 303
    assert job.result_key in response.headers["Location"]
