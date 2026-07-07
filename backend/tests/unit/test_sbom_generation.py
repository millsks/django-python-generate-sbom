"""Tests for SBOM generation, Phase 3/8 tasks, and the result endpoint (Story 3.4)."""

import json
from collections.abc import Iterator
from dataclasses import asdict
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.document import _cyclonedx_license, _spdx_license, _spdx_purl
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
from generate_sbom.users.services import create_org, register_user

PKGS = [PackageSpec(name="django", version="5.2.1"), PackageSpec(name="asgiref", version="3.8.1")]
PROV = Provenance(
    application_id="APP-1",
    component_name="web",
    repository_url="https://github.com/acme/web",
    source_branch="main",
)
_NO_UPDATE = "celery.app.task.Task.update_state"

# One map exercising every CycloneDX license shape (Story 8.25, AC #1/#2).
LICENSED_PKGS = [
    PackageSpec(name="django", version="5.2.1"),  # known SPDX id
    PackageSpec(name="dual", version="1.0"),  # SPDX expression
    PackageSpec(name="weird", version="2.0"),  # non-SPDX free text → named license
    PackageSpec(name="asgiref", version="3.8.1"),  # unknown → no license entry
]
LICENSE_MAP: dict[tuple[str, str], str | None] = {
    ("django", "5.2.1"): "BSD-3-Clause",
    ("dual", "1.0"): "Apache-2.0 OR MIT",
    ("weird", "2.0"): "Weird Custom License",
    ("asgiref", "3.8.1"): None,
}


# --- pure serializers (AC #1, #2, #3) -------------------------------------------------


def test_cyclonedx_emits_license_per_component_via_shared_map() -> None:
    content, _ = generate_sbom_document(LICENSED_PKGS, "cyclonedx-json", PROV, LICENSE_MAP)
    components = {c["name"]: c for c in json.loads(content)["components"]}
    # Known SPDX id, SPDX expression, and free-text name each surface via the viewer parse-back.
    assert _cyclonedx_license(components["django"].get("licenses")) == "BSD-3-Clause"
    assert _cyclonedx_license(components["dual"].get("licenses")) == "Apache-2.0 OR MIT"
    assert _cyclonedx_license(components["weird"].get("licenses")) == "Weird Custom License"
    # Unknown license → no entry (AC #2), which the viewer maps back to None → "—".
    assert not components["asgiref"].get("licenses")
    assert _cyclonedx_license(components["asgiref"].get("licenses")) is None


def test_cyclonedx_without_license_map_omits_all_licenses() -> None:
    content, _ = generate_sbom_document(PKGS, "cyclonedx-json", PROV)
    assert all(not c.get("licenses") for c in json.loads(content)["components"])


def test_spdx_sets_license_concluded_and_noassertion() -> None:
    content, _ = generate_sbom_document(LICENSED_PKGS, "spdx-json", PROV, LICENSE_MAP)
    packages = {p["name"]: p for p in json.loads(content)["packages"]}
    assert packages["django"]["licenseConcluded"] == "BSD-3-Clause"
    assert packages["django"]["licenseDeclared"] == "BSD-3-Clause"
    assert _spdx_license(packages["django"]) == "BSD-3-Clause"
    # Unknown → NOASSERTION, which the viewer treats as no license (AC #2).
    assert packages["asgiref"]["licenseConcluded"] == "NOASSERTION"
    assert _spdx_license(packages["asgiref"]) is None


def test_cyclonedx_records_ecosystem_property_and_purl_type() -> None:
    # Story 8.26: each component carries a package:ecosystem property and a purl whose type
    # reflects the ecosystem — pypi and conda are distinguished (dedupe key for Story 16.3).
    pkgs = [
        PackageSpec(name="django", version="5.2.1", ecosystem="pypi"),
        PackageSpec(name="numpy", version="1.26.0", ecosystem="conda"),
    ]
    content, _ = generate_sbom_document(pkgs, "cyclonedx-json", PROV)
    components = {c["name"]: c for c in json.loads(content)["components"]}
    django_props = {p["name"]: p["value"] for p in components["django"]["properties"]}
    numpy_props = {p["name"]: p["value"] for p in components["numpy"]["properties"]}
    assert django_props["package:ecosystem"] == "pypi"
    assert numpy_props["package:ecosystem"] == "conda"
    assert components["django"]["purl"] == "pkg:pypi/django@5.2.1"
    assert components["numpy"]["purl"] == "pkg:conda/numpy@1.26.0"


def test_spdx_purl_type_reflects_ecosystem() -> None:
    # Story 8.26: the SPDX purl is no longer hardcoded to pypi — a conda package is pkg:conda.
    pkgs = [
        PackageSpec(name="django", version="5.2.1", ecosystem="pypi"),
        PackageSpec(name="numpy", version="1.26.0", ecosystem="conda"),
    ]
    content, _ = generate_sbom_document(pkgs, "spdx-json", PROV)
    purls = {p["name"]: _spdx_purl(p.get("externalRefs")) for p in json.loads(content)["packages"]}
    assert purls["django"] == "pkg:pypi/django@5.2.1"
    assert purls["numpy"] == "pkg:conda/numpy@1.26.0"


def test_unknown_ecosystem_falls_back_to_pypi_without_raising() -> None:
    # Story 8.26 AC #3: a missing/unexpected ecosystem degrades to pypi and never raises.
    pkgs = [PackageSpec(name="mystery", version="1.0", ecosystem="")]
    cdx, _ = generate_sbom_document(pkgs, "cyclonedx-json", PROV)
    component = json.loads(cdx)["components"][0]
    props = {p["name"]: p["value"] for p in component["properties"]}
    assert props["package:ecosystem"] == "pypi"
    assert component["purl"] == "pkg:pypi/mystery@1.0"
    spdx, _ = generate_sbom_document(pkgs, "spdx-json", PROV)
    pkg = next(p for p in json.loads(spdx)["packages"] if p["name"] == "mystery")
    purl = next(r["referenceLocator"] for r in pkg["externalRefs"] if r["referenceType"] == "purl")
    assert purl == "pkg:pypi/mystery@1.0"


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


@pytest.fixture(autouse=True)
def _no_license_network() -> Iterator[None]:
    """Phase 3 now resolves licenses over PyPI; stub the resolver so task tests never hit the network."""
    with patch("generate_sbom.tasks.sbom_pipeline.license_service.build_license_map", return_value={}):
        yield


def _make_job(output_format: str = "cyclonedx-json", email: str = "alice@example.com") -> SBOMJob:
    user = register_user(email=email, password="pw12345678")
    org = create_org(name=user.email.split("@")[0], admin_user=user)
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
    # Phase 3 records the key + count; Phase 8 finalizes by task_id alone (reads the DB).
    from generate_sbom.sbom.services import record_generation

    record_generation(str(job.task_id), "sbom-results/x/y/sbom.json", 5)
    with patch(_NO_UPDATE):
        persist_artifacts.apply(args=(str(job.task_id),)).get()

    job.refresh_from_db()
    assert job.status == SBOMJob.Status.SUCCESS
    assert job.result_key == "sbom-results/x/y/sbom.json"
    assert job.summary_stats == {"total_packages": 5}
    assert job.progress == 100
    assert job.completed_at is not None
    assert abs((job.artifacts_expire_at - job.completed_at) - timedelta(days=30)).total_seconds() < 5


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
    create_org(name="bob", admin_user=register_user(email="bob@example.com", password="pw12345678"))

    response = _login("bob@example.com").get(f"/api/v1/sbom/result/{job.task_id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_result_endpoint_not_ready_404() -> None:
    job = _make_job()  # PENDING, no result_key
    response = _login().get(f"/api/v1/sbom/result/{job.task_id}/")
    assert response.status_code == 404
    assert response.data["code"] == "not_ready"
