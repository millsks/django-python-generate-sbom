"""Tests for the Phase 7 task and the version currency endpoint (Story 4.5)."""

import json
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from generate_sbom.analysis.models import AnalysisReport
from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.tasks.analysis import check_version_currency
from generate_sbom.users.services import register_user

_NO_UPDATE = "celery.app.task.Task.update_state"
PIXI_LOCK = b'version: 5\npackages:\n  - name: django\n    version: "4.2.0"\n'
_REPORT = {
    "packages": [{"name": "django", "installed": "4.2.0", "latest": "5.2.0", "currency": "current", "lts": "4.2"}],
    "summary": {"current": 1, "behind-1": 0, "behind-2+": 0, "unknown": 0},
}


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _make_job(email: str = "alice@example.com") -> SBOMJob:
    user = register_user(email=email, password="pw12345678")
    org = user.org_memberships.select_related("org").get().org
    upload = ManifestUpload(
        org=org,
        user=user,
        detected_format=ManifestUpload.Format.PIXI_LOCK,
        original_filename="pixi.lock",
        application_id="A",
        component_name="c",
        repository_url="https://github.com/a/b",
        source_branch="main",
    )
    upload.file.save("pixi.lock", ContentFile(PIXI_LOCK), save=False)
    upload.save()
    return SBOMJob.objects.create(org=org, manifest=upload, output_format="cyclonedx-json")


def _login(email: str = "alice@example.com") -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": "pw12345678"}, format="json")
    return client


@pytest.mark.django_db
def test_phase7_writes_artifact_and_returns_envelope() -> None:
    job = _make_job()
    with patch(_NO_UPDATE), patch("generate_sbom.tasks.analysis.versions_service.classify", return_value=_REPORT):
        envelope = check_version_currency.apply(args=({"task_id": str(job.task_id)},)).get()

    artifact_key = f"sbom-results/{job.org_id}/{job.task_id}/versions.json"
    assert envelope["report_type"] == "version"
    assert envelope["artifact_key"] == artifact_key
    assert envelope["summary"] == _REPORT["summary"]
    assert envelope["failed"] is False
    with default_storage.open(artifact_key) as handle:
        assert json.loads(handle.read())["summary"]["current"] == 1


@pytest.mark.django_db
def test_version_report_endpoint_json_inline_and_cross_org_404() -> None:
    job = _make_job()
    artifact_key = f"sbom-results/{job.org_id}/{job.task_id}/versions.json"
    default_storage.save(artifact_key, ContentFile(json.dumps(_REPORT).encode()))
    AnalysisReport.objects.create(job=job, report_type=AnalysisReport.ReportType.VERSION, artifact_key=artifact_key)

    ok = _login().get(f"/api/v1/sbom/result/{job.task_id}/reports/versions/")
    assert ok.status_code == 200
    assert ok.data == _REPORT

    register_user(email="bob@example.com", password="pw12345678")
    cross = _login("bob@example.com").get(f"/api/v1/sbom/result/{job.task_id}/reports/versions/")
    assert cross.status_code == 404
