"""SBOM document serializers (Story 3.4, Phase 3).

Pure, I/O-free functions: the shared resolved package list plus provenance in,
serialized SBOM bytes out. Format selection alone picks the serializer (AC #3) —
CycloneDX 1.6 via ``cyclonedx-python-lib``, SPDX 2.3 via ``lib4sbom``. The four
provenance fields (FR-3.8) are embedded in the document metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .parsers import PackageSpec

# Internal serializer ids (OUTPUT_FORMAT_MAP values).
CYCLONEDX_JSON = "cyclonedx-json"
CYCLONEDX_XML = "cyclonedx-xml"
SPDX_JSON = "spdx-json"

_MEDIA_TYPES = {
    CYCLONEDX_JSON: "application/json",
    CYCLONEDX_XML: "application/xml",
    SPDX_JSON: "application/json",
}
_EXTENSIONS = {
    CYCLONEDX_JSON: "json",
    CYCLONEDX_XML: "xml",
    SPDX_JSON: "json",
}


class SBOMGenerationError(Exception):
    """SBOM document serialization failed (Phase 3 hard-fail boundary, FR-4.5)."""


@dataclass(frozen=True)
class Provenance:
    """The four provenance fields carried from the manifest upload (FR-3.8)."""

    application_id: str
    component_name: str
    repository_url: str
    source_branch: str


def sbom_extension(output_format: str) -> str:
    """Return the file extension for a serializer id (e.g. ``json``, ``xml``)."""
    try:
        return _EXTENSIONS[output_format]
    except KeyError as exc:
        raise SBOMGenerationError(f"Unknown output format: {output_format!r}") from exc


def generate_sbom_document(
    packages: list[PackageSpec], output_format: str, provenance: Provenance
) -> tuple[bytes, str]:
    """Serialize the resolved package list to an SBOM document (bytes, media_type)."""
    try:
        if output_format in (CYCLONEDX_JSON, CYCLONEDX_XML):
            text = _generate_cyclonedx(packages, provenance, output_format)
        elif output_format == SPDX_JSON:
            text = _generate_spdx(packages, provenance)
        else:
            raise SBOMGenerationError(f"Unknown output format: {output_format!r}")
    except SBOMGenerationError:
        raise
    except Exception as exc:  # library-level failure → hard fail (FR-4.5)
        raise SBOMGenerationError(f"SBOM serialization failed for {output_format!r}: {exc}") from exc
    return text.encode("utf-8"), _MEDIA_TYPES[output_format]


def _generate_cyclonedx(packages: list[PackageSpec], provenance: Provenance, output_format: str) -> str:
    """Build a CycloneDX 1.6 document (JSON or XML) with provenance metadata."""
    from cyclonedx.model import ExternalReference, ExternalReferenceType, Property, XsUri
    from cyclonedx.model.bom import Bom
    from cyclonedx.model.component import Component, ComponentType
    from cyclonedx.output import make_outputter
    from cyclonedx.schema import OutputFormat, SchemaVersion

    bom = Bom()
    root = Component(
        name=provenance.component_name,
        type=ComponentType.APPLICATION,
        bom_ref=provenance.component_name,
    )
    root.external_references.add(
        ExternalReference(type=ExternalReferenceType.VCS, url=XsUri(provenance.repository_url))
    )
    root.properties.add(Property(name="application:id", value=provenance.application_id))
    root.properties.add(Property(name="vcs:branch", value=provenance.source_branch))
    bom.metadata.component = root

    components = []
    for pkg in packages:
        component = Component(
            name=pkg.name,
            version=pkg.version,
            type=ComponentType.LIBRARY,
            bom_ref=f"{pkg.name}@{pkg.version}",
        )
        bom.components.add(component)
        components.append(component)
    bom.register_dependency(root, components)

    schema_format = OutputFormat.JSON if output_format == CYCLONEDX_JSON else OutputFormat.XML
    outputter = make_outputter(bom, schema_format, SchemaVersion.V1_6)
    return outputter.output_as_string(indent=2)


def _generate_spdx(packages: list[PackageSpec], provenance: Provenance) -> str:
    """Build an SPDX 2.3 JSON document; embed provenance best-effort (FR-3.8)."""
    from lib4sbom.data.document import SBOMDocument
    from lib4sbom.data.package import SBOMPackage
    from lib4sbom.generator import SBOMGenerator
    from lib4sbom.sbom import SBOM

    document = SBOMDocument()
    document.initialise()
    document.set_name(provenance.component_name)

    packages_dict = {}
    root = SBOMPackage()
    root.initialise()
    root.set_name(provenance.component_name)
    root.set_version("NOASSERTION")
    root.set_type("application")
    root.set_externalreference("PACKAGE-MANAGER", "vcs", provenance.repository_url)
    root.set_comment(f"application:id={provenance.application_id}; vcs:branch={provenance.source_branch}")
    packages_dict[(provenance.component_name, "NOASSERTION")] = root.get_package()

    for pkg in packages:
        entry = SBOMPackage()
        entry.initialise()
        entry.set_name(pkg.name)
        entry.set_version(pkg.version)
        entry.set_type("library")
        entry.set_purl(f"pkg:pypi/{pkg.name}@{pkg.version}")
        packages_dict[(pkg.name, pkg.version)] = entry.get_package()

    sbom = SBOM()
    sbom.set_type("spdx")
    sbom.add_document(document.get_document())
    sbom.add_packages(packages_dict)

    generator = SBOMGenerator(sbom_type="spdx", format="json")
    generator.generate(project_name=provenance.component_name, sbom_data=sbom.get_sbom(), send_to_output=False)
    return json.dumps(generator.get_sbom(), indent=2)
