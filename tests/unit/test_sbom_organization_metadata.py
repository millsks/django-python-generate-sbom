"""Story 22.14: the organization is carried into the generated SBOM as its supplier.

The organization is chosen on the upload form and, until now, went no further than the
`SBOMJob` row. An SBOM that omits it is missing the one field that says *whose* software
this describes — which is the whole point of filing a job against a line of business.

It goes into each format's **own** supplier slot rather than a custom property: CycloneDX
`metadata.supplier`, SPDX `PackageSupplier`. Other SBOM tooling already reads those; a
`Property(name="organization")` would only be legible to this application, which defeats
producing a standard document.
"""

from __future__ import annotations

import json

import pytest

from inventory.sbom.generation import (
    CYCLONEDX_JSON,
    CYCLONEDX_XML,
    SPDX_JSON,
    Provenance,
    generate_sbom_document,
)
from inventory.sbom.parsers import PackageSpec

PKGS = [PackageSpec(name="django", version="5.2.1")]
ORG_NAME = "ORG002"


def _provenance(organization: str = ORG_NAME) -> Provenance:
    return Provenance(
        application_id="APP-1",
        component_name="billing-api",
        repository_url="https://github.com/acme/billing-api",
        source_branch="main",
        organization=organization,
    )


def _document(output_format: str, organization: str = ORG_NAME) -> str:
    """Generate and decode a document. The generator returns ``(bytes, media_type)``."""
    payload, _media_type = generate_sbom_document(PKGS, output_format, _provenance(organization))
    return payload.decode()


# --- CycloneDX ---------------------------------------------------------------------------


def test_cyclonedx_names_the_organization_as_the_document_supplier() -> None:
    document = _document(CYCLONEDX_JSON)

    supplier = json.loads(document)["metadata"]["supplier"]

    assert supplier["name"] == ORG_NAME


def test_cyclonedx_xml_carries_the_supplier_too() -> None:
    """The XML serializer is a separate code path in cyclonedx-python-lib, not a re-encoding."""
    document = _document(CYCLONEDX_XML)

    assert "<supplier>" in document
    assert ORG_NAME in document


def test_the_existing_provenance_properties_are_untouched() -> None:
    """Adding the supplier must not disturb FR-3.8's four fields.

    They are asserted here rather than only in `test_sbom_generation.py` because this is the
    change that could silently drop one — the component metadata is rebuilt around them.
    """
    document = json.loads(_document(CYCLONEDX_JSON))

    component = document["metadata"]["component"]
    properties = {p["name"]: p["value"] for p in component["properties"]}

    assert component["name"] == "billing-api"
    assert properties["application:id"] == "APP-1"
    assert properties["vcs:branch"] == "main"
    assert any(ref["url"] == "https://github.com/acme/billing-api" for ref in component["externalReferences"])


# --- SPDX ---------------------------------------------------------------------------------


def test_spdx_names_the_organization_as_the_package_supplier() -> None:
    document = json.loads(_document(SPDX_JSON))

    root = next(p for p in document["packages"] if p["name"] == "billing-api")

    assert root["supplier"] == f"Organization: {ORG_NAME}"


# --- The awkward values -------------------------------------------------------------------


@pytest.mark.parametrize("output_format", [CYCLONEDX_JSON, CYCLONEDX_XML, SPDX_JSON])
def test_a_document_still_generates_when_the_organization_is_empty(output_format: str) -> None:
    """Generation is a hard-fail phase (FR-4.5), so a missing name must not abort the job.

    Reachable through the API, which does not require an org name to be non-empty, and
    through any job whose org was renamed to blank. Losing an SBOM over a metadata field
    would be a worse outcome than a document without a supplier.
    """
    document = _document(output_format, organization="")

    assert document
    assert "billing-api" in document


def test_an_organization_name_with_markup_does_not_break_the_xml() -> None:
    """Org names are free text from `orgs.yml`; the XML serializer must escape them.

    An unescaped `&` is enough to produce a document no consumer can parse — a corrupted
    artifact rather than a visibly failed job, which is the worse failure of the two.
    """
    document = _document(CYCLONEDX_XML, organization="Smith & Sons <ops>")

    assert "Smith &amp; Sons" in document
    assert "<ops>" not in document

    from xml.etree import ElementTree

    ElementTree.fromstring(document)


# --- The whole way through --------------------------------------------------------------


@pytest.mark.django_db
def test_the_org_chosen_on_the_upload_form_reaches_the_document() -> None:
    """The claim this story actually makes, asserted end to end.

    The generator unit tests above prove a `Provenance` becomes a supplier. They cannot catch
    the more likely regression: `build_provenance` reading the acting request's org, or the
    manifest's `org` never being set. Those would leave every generator test green and every
    real SBOM stamped with the wrong tenant.
    """
    from django.core.files.base import ContentFile

    from inventory.manifests.models import ManifestUpload
    from inventory.sbom.services import build_provenance
    from inventory.users.services import create_org

    filed_against = create_org(name="Capital Markets", admin_user=None)
    create_org(name="Somewhere Else", admin_user=None)  # a second org, to make a mix-up visible

    upload = ManifestUpload(
        org=filed_against,
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
        application_id="APP-9",
        component_name="ledger",
        repository_url="https://github.com/acme/ledger",
        source_branch="main",
    )
    upload.file.save("requirements.txt", ContentFile(b"django==5.2.1\n"), save=False)
    upload.save()

    payload, _ = generate_sbom_document(PKGS, CYCLONEDX_JSON, build_provenance(upload))

    assert json.loads(payload.decode())["metadata"]["supplier"]["name"] == "Capital Markets"
