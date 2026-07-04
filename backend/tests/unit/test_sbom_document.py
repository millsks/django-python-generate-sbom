"""Tests for the SBOM viewer parser + inline content endpoint (Story 8.6)."""

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.document import normalize_components, parse_metadata
from generate_sbom.sbom.generation import Provenance, generate_sbom_document
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.parsers import PackageSpec
from generate_sbom.sbom.services import finalize_job
from generate_sbom.users.services import register_user

PKGS = [PackageSpec(name="django", version="5.2.1"), PackageSpec(name="asgiref", version="3.8.1")]
PROV = Provenance(
    application_id="APP-1", component_name="web", repository_url="https://github.com/acme/web", source_branch="main"
)


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


# --- pure parser: round-trip real generated documents --------------------------------


@pytest.mark.parametrize("output_format", ["cyclonedx-json", "cyclonedx-xml", "spdx-json"])
def test_normalize_extracts_components(output_format: str) -> None:
    raw, _ = generate_sbom_document(PKGS, output_format, PROV)

    components = normalize_components(raw, output_format)

    by_name = {c["name"]: c for c in components}
    # Both dependencies are present with their versions, regardless of format.
    assert by_name["django"]["version"] == "5.2.1"
    assert by_name["asgiref"]["version"] == "3.8.1"


def test_normalize_unknown_format_is_empty() -> None:
    assert normalize_components(b"{}", "totally-made-up") == []


@pytest.mark.parametrize("output_format", ["cyclonedx-json", "cyclonedx-xml", "spdx-json"])
def test_direct_transitive_round_trips_through_the_document(output_format: str) -> None:
    # Story 8.4: the direct/transitive relationship is encoded in the SBOM and read back.
    pkgs = [
        PackageSpec(name="django", version="5.2.1", relationship="direct"),
        PackageSpec(name="asgiref", version="3.8.1", relationship="transitive"),
    ]
    raw, _ = generate_sbom_document(pkgs, output_format, PROV)

    by_name = {c["name"]: c["relationship"] for c in normalize_components(raw, output_format)}

    assert by_name["django"] == "direct"
    assert by_name["asgiref"] == "transitive"


@pytest.mark.parametrize("output_format", ["cyclonedx-json", "cyclonedx-xml", "spdx-json"])
def test_all_unknown_packages_are_not_forced_into_a_split(output_format: str) -> None:
    # Story 8.4 AC #3: unknown-relationship packages (e.g. from pixi.lock) are never
    # falsely labeled direct/transitive; the document still generates and parses.
    pkgs = [PackageSpec(name="numpy", version="1.26.0"), PackageSpec(name="requests", version="2.32.3")]
    raw, _ = generate_sbom_document(pkgs, output_format, PROV)

    rels = {c["relationship"] for c in normalize_components(raw, output_format) if c["name"] in {"numpy", "requests"}}

    assert rels <= {"unknown", None}


# --- document metadata block (Story 8.11) --------------------------------------------


@pytest.mark.parametrize("output_format", ["cyclonedx-json", "cyclonedx-xml", "spdx-json"])
def test_parse_metadata_reads_provenance_and_document_info(output_format: str) -> None:
    # Story 8.11: the provenance embedded at generation is read back into a metadata dict.
    raw, _ = generate_sbom_document(PKGS, output_format, PROV)

    metadata = parse_metadata(raw, output_format)

    assert metadata["component_name"] == "web"
    assert metadata["application_id"] == "APP-1"
    assert metadata["repository_url"] == "https://github.com/acme/web"
    assert metadata["source_branch"] == "main"
    assert metadata["format"] in {"CycloneDX", "SPDX"}
    assert metadata["spec_version"]  # e.g. "1.6" (CycloneDX) or "2.3" (SPDX)
    assert metadata["generated"]  # a serialized timestamp


@pytest.mark.parametrize("output_format", ["cyclonedx-json", "cyclonedx-xml", "spdx-json"])
def test_parse_metadata_omits_absent_provenance_fields(output_format: str) -> None:
    # Story 8.11 AC #5: partial provenance yields no blank keys (empty strings dropped).
    partial = Provenance(application_id="", component_name="web", repository_url="", source_branch="")
    raw, _ = generate_sbom_document(PKGS, output_format, partial)

    metadata = parse_metadata(raw, output_format)

    assert metadata["component_name"] == "web"
    assert "application_id" not in metadata
    assert "repository_url" not in metadata
    assert "source_branch" not in metadata


def test_parse_metadata_unknown_format_is_empty() -> None:
    assert parse_metadata(b"{}", "totally-made-up") == {}


@pytest.mark.parametrize(
    ("output_format", "meta_marker", "components_marker"),
    [
        ("cyclonedx-json", '"metadata"', '"components"'),
        ("cyclonedx-xml", "<metadata>", "<components>"),
        ("spdx-json", '"creationInfo"', '"packages"'),
    ],
)
def test_metadata_precedes_components_in_document(output_format: str, meta_marker: str, components_marker: str) -> None:
    # Story 8.11 AC #2: the serialized document leads with metadata before the component data.
    raw, _ = generate_sbom_document(PKGS, output_format, PROV)
    text = raw.decode("utf-8")

    assert text.index(meta_marker) < text.index(components_marker)


# --- inline content endpoint ---------------------------------------------------------


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


def _complete(job: SBOMJob) -> str:
    raw, _ = generate_sbom_document(PKGS, job.output_format, PROV)
    result_key = f"sbom-results/{job.org_id}/{job.task_id}/sbom.json"
    default_storage.save(result_key, ContentFile(raw))
    finalize_job(str(job.task_id), result_key, {"total_packages": 2})
    return result_key


@pytest.mark.django_db
def test_document_endpoint_returns_components_and_raw() -> None:
    job = _make_job()
    _complete(job)

    response = _login().get(f"/api/v1/sbom/document/{job.task_id}/")

    assert response.status_code == 200
    assert response.data["format"] == "cyclonedx-json"
    assert response.data["metadata"]["component_name"] == "web"  # parsed provenance (Story 8.11)
    assert response.data["metadata"]["repository_url"] == "https://github.com/acme/web"
    assert {c["name"] for c in response.data["components"]} == {"django", "asgiref"}
    assert '"bomFormat": "CycloneDX"' in response.data["raw"]  # raw is the exact document text


@pytest.mark.django_db
def test_document_endpoint_cross_org_404() -> None:
    job = _make_job()
    _complete(job)
    register_user(email="bob@example.com", password="pw12345678")

    response = _login("bob@example.com").get(f"/api/v1/sbom/document/{job.task_id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_document_endpoint_not_ready_404() -> None:
    job = _make_job()  # PENDING, no result_key
    response = _login().get(f"/api/v1/sbom/document/{job.task_id}/")
    assert response.status_code == 404
    assert response.data["code"] == "not_ready"
