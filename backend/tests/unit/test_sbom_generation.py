"""Tests for SBOM generation, Phase 3/8 tasks, and the result endpoint (Story 3.4)."""

import json
from dataclasses import asdict
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.generation import (
    Provenance,
    SBOMGenerationError,
    generate_sbom_document,
    sbom_extension,
)
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.parsers import PackageSpec
from generate_sbom.sbom.services import finalize_job
from generate_sbom.tasks.sbom_pipeline import generate_sbom_document as generate_phase
from generate_sbom.tasks.sbom_pipeline import persist_artifacts
from generate_sbom.users.services import register_user

PKGS = [PackageSpec(name="django", version="5.2.1"), PackageSpec(name="asgiref", version="3.8.1")]
PROV = Provenance(
    application_id="APP-1",
    component_name="web",
    repository_url="https://github.com/acme/web",
    source_branch="main",
)
_NO_UPDATE = "celery.app.task.Task.update_state"


# --- pure serializers (AC #1, #2, #3) -------------------------------------------------


def test_cyclonedx_json_embeds_provenance() -> None:
    content, media_type = generate_sbom_document(PKGS, "cyclonedx-json", PROV)
    assert media_type == "application/json"
    doc = json.loads(content)
    assert doc["specVersion"] == "1.6"
    assert doc["bomFormat"] == "CycloneDX"
    assert {c["name"] for c in doc["components"]} == {"django", "asgiref"}
    meta = doc["metadata"]["component"]
    assert meta["name"] == "web"
    props = {p["name"]: p["value"] for p in meta["properties"]}
    assert props == {"application:id": "APP-1", "vcs:branch": "main"}
    assert meta["externalReferences"][0]["url"] == "https://github.com/acme/web"


def test_cyclonedx_xml_serialization() -> None:
    content, media_type = generate_sbom_document(PKGS, "cyclonedx-xml", PROV)
    assert media_type == "application/xml"
    assert content.startswith(b"<?xml")
    assert b"cyclonedx.org/schema/bom/1.6" in content
    assert b"django" in content


def test_spdx_json_serialization() -> None:
    content, media_type = generate_sbom_document(PKGS, "spdx-json", PROV)
    assert media_type == "application/json"
    doc = json.loads(content)
    assert doc["spdxVersion"] == "SPDX-2.3"
    names = {p["name"] for p in doc["packages"]}
    assert {"django", "asgiref"} <= names
    assert "web" in names  # root application package carrying provenance


def test_same_list_only_format_selects_serializer() -> None:
    cdx, _ = generate_sbom_document(PKGS, "cyclonedx-json", PROV)
    spdx, _ = generate_sbom_document(PKGS, "spdx-json", PROV)
    assert b"CycloneDX" in cdx
    assert b"SPDX" in spdx


def test_unknown_format_raises() -> None:
    with pytest.raises(SBOMGenerationError):
        generate_sbom_document(PKGS, "bogus", PROV)


def test_library_error_is_wrapped() -> None:
    with patch("generate_sbom.sbom.generation._generate_cyclonedx", side_effect=ValueError("boom")):
        with pytest.raises(SBOMGenerationError):
            generate_sbom_document(PKGS, "cyclonedx-json", PROV)


def test_sbom_extension_maps_formats() -> None:
    assert sbom_extension("cyclonedx-json") == "json"
    assert sbom_extension("cyclonedx-xml") == "xml"
    assert sbom_extension("spdx-json") == "json"
    with pytest.raises(SBOMGenerationError):
        sbom_extension("nope")


# --- Phase 3/8 tasks + result endpoint (AC #4-#8) ------------------------------------


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _make_job(output_format: str = "cyclonedx-json", email: str = "alice@example.com") -> SBOMJob:
    user = register_user(email=email, password="pw12345678")
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


def _login(email: str = "alice@example.com") -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": "pw12345678"}, format="json")
    return client


def _prev_from(job: SBOMJob) -> dict[str, object]:
    return {"task_id": str(job.task_id), "packages": [asdict(pkg) for pkg in PKGS]}


@pytest.mark.django_db
def test_phase3_generates_and_writes_blob() -> None:
    job = _make_job()
    with patch(_NO_UPDATE):
        out = generate_phase.apply(args=(_prev_from(job),)).get()

    result_key = f"sbom-results/{job.org_id}/{job.task_id}/sbom.json"
    assert out == {
        "task_id": str(job.task_id),
        "result_key": result_key,
        "package_count": 2,
        "media_type": "application/json",
    }
    assert default_storage.exists(result_key)
    with default_storage.open(result_key) as handle:
        assert json.loads(handle.read())["specVersion"] == "1.6"


@pytest.mark.django_db
def test_phase3_serializer_error_fails_job_no_artifact() -> None:
    job = _make_job()
    with (
        patch(_NO_UPDATE),
        patch("generate_sbom.sbom.services.generate_sbom_document", side_effect=SBOMGenerationError("boom")),
    ):
        result = generate_phase.apply(args=(_prev_from(job),))

    assert result.failed()
    job.refresh_from_db()
    assert job.status == SBOMJob.Status.FAILED
    assert job.failure_reason == "sbom_generation_failed"
    assert not default_storage.exists(f"sbom-results/{job.org_id}/{job.task_id}/sbom.json")


@pytest.mark.django_db
def test_phase8_finalizes_job() -> None:
    job = _make_job()
    prev = {"task_id": str(job.task_id), "result_key": "sbom-results/x/y/sbom.json", "package_count": 5}
    with patch(_NO_UPDATE):
        persist_artifacts.apply(args=(prev,)).get()

    job.refresh_from_db()
    assert job.status == SBOMJob.Status.SUCCESS
    assert job.result_key == "sbom-results/x/y/sbom.json"
    assert job.summary_stats == {"total_packages": 5}
    assert job.progress == 100
    assert job.completed_at is not None
    assert abs((job.artifacts_expire_at - job.completed_at) - timedelta(days=10)).total_seconds() < 5


@pytest.mark.django_db
def test_result_endpoint_303_without_reading_bytes() -> None:
    job = _make_job()
    result_key = f"sbom-results/{job.org_id}/{job.task_id}/sbom.json"
    default_storage.save(result_key, ContentFile(b'{"specVersion": "1.6"}'))
    finalize_job(str(job.task_id), result_key, {"total_packages": 2})
    client = _login()

    with patch.object(default_storage, "open", side_effect=AssertionError("Django must not stream bytes")):
        response = client.get(f"/api/v1/sbom/result/{job.task_id}/")

    assert response.status_code == 303
    assert result_key in response.headers["Location"]


@pytest.mark.django_db
def test_result_endpoint_cross_org_404() -> None:
    job = _make_job()
    finalize_job(str(job.task_id), "sbom-results/x/y/sbom.json", {})
    register_user(email="bob@example.com", password="pw12345678")

    response = _login("bob@example.com").get(f"/api/v1/sbom/result/{job.task_id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_result_endpoint_not_ready_404() -> None:
    job = _make_job()  # PENDING, no result_key
    response = _login().get(f"/api/v1/sbom/result/{job.task_id}/")
    assert response.status_code == 404
    assert response.data["code"] == "not_ready"
