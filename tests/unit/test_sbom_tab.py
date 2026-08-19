"""Story 21.13: the SBOM viewer tab.

The assertion that matters most is AC #4's: the raw document must **not** ride along in the
tab's initial payload. A generated SBOM can be several megabytes, and the failure mode of
getting this wrong is a results page that is slow for exactly the projects that need it most.
"""

from __future__ import annotations

import json

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.sbom.pages import RAW_INLINE_MAX_BYTES
from inventory.users.models import Org
from inventory.users.services import create_org, register_user

PASSWORD = "pw12345678"


# A CycloneDX document carrying the enrichment written at generation time: licence (8.25),
# ecosystem + purl type (8.26), and direct/transitive relationship (8.3-8.4).
def _document(*, with_relationship: bool = True) -> bytes:
    def component(name: str, version: str, licence: str, ecosystem: str, relationship: str) -> dict:
        properties = [{"name": "package:ecosystem", "value": ecosystem}]
        if with_relationship:
            properties.append({"name": "sbom:relationship", "value": relationship})
        return {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:{ecosystem}/{name}@{version}",
            "licenses": [{"license": {"id": licence}}],
            "properties": properties,
        }

    return json.dumps(
        {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "metadata": {"component": {"name": "billing", "type": "application"}},
            "components": [
                component("zeta", "1.0.0", "MIT", "pypi", "direct"),
                component("alpha", "2.0.0", "Apache-2.0", "pypi", "transitive"),
            ],
        }
    ).encode()


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


def _job(org: Org, *, raw: bytes | None = None, purged: bool = False) -> SBOMJob:
    upload = ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
        application_id="APP",
        component_name="billing",
        repository_url="https://example.com/r",
        source_branch="main",
    )
    result_key = None
    if not purged:
        result_key = f"sboms/{upload.pk}.json"
        default_storage.save(result_key, ContentFile(raw if raw is not None else _document()))
    return SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        result_key=result_key,
        summary_stats={"total_packages": 2},
    )


@pytest.fixture
def org_client():  # type: ignore[no-untyped-def]
    user = register_user(email="dev@example.com", password=PASSWORD)
    org = create_org(name="Acme", admin_user=user)
    return _client("dev@example.com"), org


def _tab(client: Client, job: SBOMJob, **params: str) -> str:
    query = ("?" + "&".join(f"{k}={v}" for k, v in params.items())) if params else ""
    response = client.get(f"/results/{job.task_id}/tab/sbom{query}")
    assert response.status_code == 200
    return response.content.decode()


# --- AC #1/#2: the component table --------------------------------------------------------


@pytest.mark.django_db
def test_the_component_table_is_the_default_view(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert "alpha" in html and "zeta" in html
    assert "Components" in html


@pytest.mark.django_db
def test_the_table_keeps_every_enrichment_column(org_client) -> None:  # type: ignore[no-untyped-def]
    """Licence (8.25), ecosystem (8.26), and relationship (8.3-8.4) are read, not recomputed."""
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    for header in ("Name", "Version", "Type", "License", "Ecosystem", "Relationship"):
        assert header in html
    assert "MIT" in html
    assert "pypi" in html
    assert "transitive" in html


@pytest.mark.django_db
def test_the_relationship_column_is_hidden_when_no_component_has_one(org_client) -> None:  # type: ignore[no-untyped-def]
    # Mirrors the SPA's showRelationship: an all-em-dash column is worse than none.
    client, org = org_client
    job = _job(org, raw=_document(with_relationship=False))

    html = _tab(client, job)

    assert "Relationship" not in html
    assert "alpha" in html  # the rest of the table is unaffected


@pytest.mark.django_db
def test_the_metadata_block_is_preserved(org_client) -> None:  # type: ignore[no-untyped-def]
    # Story 8.11's document metadata header.
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert "CycloneDX" in html
    assert "1.6" in html


# --- AC #3: server-side sorting -----------------------------------------------------------


@pytest.mark.django_db
def test_the_default_sort_is_name_ascending(org_client) -> None:  # type: ignore[no-untyped-def]
    """Story 8.16's default, preserved."""
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert html.index("alpha") < html.index("zeta")


@pytest.mark.django_db
def test_sorting_is_driven_by_the_querystring(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    descending = _tab(client, job, sort="-name")

    assert descending.index("zeta") < descending.index("alpha")


@pytest.mark.django_db
def test_a_sorted_view_is_linkable(org_client) -> None:  # type: ignore[no-untyped-def]
    # The point of moving sorting server-side: the sort survives being shared.
    client, org = org_client
    job = _job(org)

    first = _tab(client, job, sort="-name")
    second = _tab(client, job, sort="-name")

    assert first == second
    assert second.index("zeta") < second.index("alpha")


# --- AC #4: the raw document is not in the initial payload ---------------------------------


@pytest.mark.django_db
def test_the_raw_document_is_absent_from_the_tab_payload(org_client) -> None:  # type: ignore[no-untyped-def]
    """The load-bearing assertion: a multi-megabyte document must not ride along."""
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    # A string that appears only in the raw JSON, never in the rendered table.
    assert "bomFormat" not in html
    assert "specVersion" not in html
    # ...but the raw view is reachable.
    assert f"/results/{job.task_id}/sbom/raw" in html


@pytest.mark.django_db
def test_the_raw_view_serves_the_document_on_its_own_request(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    body = client.get(f"/results/{job.task_id}/sbom/raw").content.decode()

    assert "bomFormat" in body
    assert "CycloneDX" in body


@pytest.mark.django_db
def test_an_oversized_document_offers_a_download_instead_of_inlining_it(org_client) -> None:  # type: ignore[no-untyped-def]
    """Above the cap the page declines to render megabytes of text into the DOM."""
    client, org = org_client
    padding = " " * (RAW_INLINE_MAX_BYTES + 1)
    job = _job(org, raw=b'{"bomFormat": "CycloneDX", "components": [], "pad": "' + padding.encode() + b'"}')

    body = client.get(f"/results/{job.task_id}/sbom/raw").content.decode()

    assert "too large to display" in body
    # Still a redirect to storage (AD-11), not a proxied stream — through the page's own route.
    assert f"/results/{job.task_id}/sbom/download" in body
    assert "bomFormat" not in body


# --- AC #5: unavailable is a notice, not an error -----------------------------------------


@pytest.mark.django_db
def test_a_purged_artifact_shows_a_notice(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, purged=True)

    html = _tab(client, job)

    assert "not available" in html
    assert "retention" in html


@pytest.mark.django_db
def test_the_raw_view_shows_the_same_notice_when_unavailable(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, purged=True)

    body = client.get(f"/results/{job.task_id}/sbom/raw").content.decode()

    assert "not available" in body


@pytest.mark.django_db
def test_a_missing_blob_is_a_notice_not_a_crash(org_client) -> None:  # type: ignore[no-untyped-def]
    """The row still claims a result_key, but the bytes are gone — a real post-purge race."""
    client, org = org_client
    job = _job(org)
    default_storage.delete(job.result_key)

    html = _tab(client, job)

    assert "not available" in html


# --- Access --------------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_raw_view_serves_another_orgs_document(org_client) -> None:  # type: ignore[no-untyped-def]
    client, _ = org_client
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org)

    assert client.get(f"/results/{theirs.task_id}/sbom/raw").status_code == 200


@pytest.mark.django_db
def test_the_shell_renders_the_sbom_tab_server_side(org_client) -> None:  # type: ignore[no-untyped-def]
    # ?tab=sbom must work on a cold load, not only via htmx.
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}?tab=sbom").content.decode()

    assert "alpha" in html
    assert "bomFormat" not in html
