"""Parse a stored SBOM document into a normalized component list (Story 8.6).

Pure, I/O-free functions (AD-3): the raw SBOM bytes + its serializer id in, a
flat list of ``{name, version, type, purl, license, relationship}`` dicts out —
so the SPA never needs a CycloneDX/SPDX/JSON/XML parser. ``relationship`` is
always ``None`` until the direct/transitive work (Stories 8.3/8.4) populates it.
"""

from __future__ import annotations

import json
from typing import Any
from xml.etree import ElementTree

from .generation import CYCLONEDX_JSON, CYCLONEDX_XML, SPDX_JSON


def normalize_components(raw: bytes, output_format: str) -> list[dict[str, Any]]:
    """Return the SBOM's components as normalized dicts for the viewer (Story 8.6)."""
    text = raw.decode("utf-8")
    if output_format == CYCLONEDX_JSON:
        return _from_cyclonedx_json(text)
    if output_format == CYCLONEDX_XML:
        return _from_cyclonedx_xml(text)
    if output_format == SPDX_JSON:
        return _from_spdx_json(text)
    return []


def _component(name: str, version: str, type_: str | None, purl: str | None, license_: str | None) -> dict[str, Any]:
    return {
        "name": name,
        "version": version,
        "type": (type_ or "").lower() or None,
        "purl": purl or None,
        "license": license_ or None,
        "relationship": None,  # populated by Stories 8.3/8.4
    }


def _from_cyclonedx_json(text: str) -> list[dict[str, Any]]:
    doc = json.loads(text)
    components = []
    for comp in doc.get("components", []) or []:
        components.append(
            _component(
                name=str(comp.get("name", "")),
                version=str(comp.get("version", "")),
                type_=comp.get("type"),
                purl=comp.get("purl"),
                license_=_cyclonedx_license(comp.get("licenses")),
            )
        )
    return components


def _cyclonedx_license(licenses: Any) -> str | None:
    """Join a CycloneDX component's licenses (id/name or expression) into a string."""
    if not isinstance(licenses, list):
        return None
    names: list[str] = []
    for entry in licenses:
        if not isinstance(entry, dict):
            continue
        if "expression" in entry:
            names.append(str(entry["expression"]))
        elif isinstance(entry.get("license"), dict):
            lic = entry["license"]
            value = lic.get("id") or lic.get("name")
            if value:
                names.append(str(value))
    return ", ".join(names) or None


def _local(tag: str) -> str:
    """Strip an XML namespace so ``{ns}component`` matches as ``component``."""
    return tag.rsplit("}", 1)[-1]


def _from_cyclonedx_xml(text: str) -> list[dict[str, Any]]:
    # Parses our own trusted, already-generated CycloneDX document (not user input).
    root = ElementTree.fromstring(text)
    components = []
    for element in root.iter():
        if _local(element.tag) != "component":
            continue
        fields: dict[str, str] = {}
        purl: str | None = None
        license_parts: list[str] = []
        for child in element:
            local = _local(child.tag)
            if local in ("name", "version") and child.text:
                fields[local] = child.text.strip()
            elif local == "purl" and child.text:
                purl = child.text.strip()
            elif local == "licenses":
                license_parts.extend(_cyclonedx_xml_licenses(child))
        components.append(
            _component(
                name=fields.get("name", ""),
                version=fields.get("version", ""),
                type_=element.get("type"),
                purl=purl,
                license_=", ".join(license_parts) or None,
            )
        )
    return components


def _cyclonedx_xml_licenses(licenses_el: ElementTree.Element) -> list[str]:
    """Extract license id/name/expression text from a CycloneDX XML ``<licenses>`` node."""
    parts: list[str] = []
    for node in licenses_el.iter():
        local = _local(node.tag)
        if local in ("id", "name", "expression") and node.text:
            parts.append(node.text.strip())
    return parts


def _from_spdx_json(text: str) -> list[dict[str, Any]]:
    doc = json.loads(text)
    components = []
    for pkg in doc.get("packages", []) or []:
        components.append(
            _component(
                name=str(pkg.get("name", "")),
                version=str(pkg.get("versionInfo", "")),
                type_=pkg.get("primaryPackagePurpose"),
                purl=_spdx_purl(pkg.get("externalRefs")),
                license_=_spdx_license(pkg),
            )
        )
    return components


def _spdx_purl(external_refs: Any) -> str | None:
    if not isinstance(external_refs, list):
        return None
    for ref in external_refs:
        if isinstance(ref, dict) and ref.get("referenceType") == "purl":
            return str(ref.get("referenceLocator", "")) or None
    return None


def _spdx_license(pkg: dict[str, Any]) -> str | None:
    """Prefer concluded over declared; treat NOASSERTION/NONE as unknown."""
    for field in ("licenseConcluded", "licenseDeclared"):
        value = pkg.get(field)
        if value and value not in ("NOASSERTION", "NONE"):
            return str(value)
    return None
