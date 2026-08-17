"""Parse a stored SBOM document into a normalized component list (Story 8.6).

Pure, I/O-free functions (AD-3): the raw SBOM bytes + its serializer id in, a
flat list of ``{name, version, type, purl, license, relationship, ecosystem}`` dicts out —
so the SPA never needs a CycloneDX/SPDX/JSON/XML parser. ``relationship`` is
always ``None`` until the direct/transitive work (Stories 8.3/8.4) populates it.
"""

from __future__ import annotations

import json
from typing import Any
from xml.etree import ElementTree

from .generation import CYCLONEDX_JSON, CYCLONEDX_XML, SPDX_JSON
from .parsers import PYPI


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


def parse_metadata(raw: bytes, output_format: str) -> dict[str, Any]:
    """Return the SBOM's document metadata for the viewer header (Story 8.11).

    Reads back the provenance already embedded at generation — CycloneDX root-component
    ``application:id``/``vcs:branch`` properties plus a VCS external reference; SPDX a
    root-package comment plus external reference — together with the format, spec version,
    and generated timestamp. Absent fields are omitted so the viewer renders no blank rows.
    """
    text = raw.decode("utf-8")
    if output_format == CYCLONEDX_JSON:
        return _metadata_from_cyclonedx_json(text)
    if output_format == CYCLONEDX_XML:
        return _metadata_from_cyclonedx_xml(text)
    if output_format == SPDX_JSON:
        return _metadata_from_spdx_json(text)
    return {}


def _metadata(**fields: str | None) -> dict[str, Any]:
    """Drop absent (falsy) fields so the endpoint omits them gracefully (AC #5)."""
    return {name: value for name, value in fields.items() if value}


def _metadata_from_cyclonedx_json(text: str) -> dict[str, Any]:
    doc = json.loads(text)
    meta = doc.get("metadata") or {}
    component = meta.get("component") or {}
    props = {
        prop.get("name"): prop.get("value") for prop in component.get("properties", []) or [] if isinstance(prop, dict)
    }
    repository_url: str | None = None
    for ref in component.get("externalReferences", []) or []:
        if isinstance(ref, dict) and ref.get("type") == "vcs":
            repository_url = ref.get("url")
            break
    return _metadata(
        component_name=component.get("name"),
        application_id=props.get("application:id"),
        repository_url=repository_url,
        source_branch=props.get("vcs:branch"),
        format=doc.get("bomFormat"),
        spec_version=doc.get("specVersion"),
        generated=meta.get("timestamp"),
    )


def _metadata_from_cyclonedx_xml(text: str) -> dict[str, Any]:
    # Parses our own trusted, already-generated CycloneDX document (not user input).
    root = ElementTree.fromstring(text)
    spec_version = _cyclonedx_xml_spec_version(root.tag)
    metadata_el = next((el for el in root if _local(el.tag) == "metadata"), None)
    if metadata_el is None:
        return _metadata(format="CycloneDX", spec_version=spec_version)
    timestamp: str | None = None
    component_el: ElementTree.Element | None = None
    for child in metadata_el:
        local = _local(child.tag)
        if local == "timestamp" and child.text:
            timestamp = child.text.strip()
        elif local == "component":
            component_el = child
    name: str | None = None
    repository_url: str | None = None
    props: dict[str, str] = {}
    if component_el is not None:
        for child in component_el:
            local = _local(child.tag)
            if local == "name" and child.text:
                name = child.text.strip()
            elif local == "externalReferences":
                repository_url = _cyclonedx_xml_vcs_url(child) or repository_url
            elif local == "properties":
                props = _cyclonedx_xml_properties(child)
    return _metadata(
        component_name=name,
        application_id=props.get("application:id"),
        repository_url=repository_url,
        source_branch=props.get("vcs:branch"),
        format="CycloneDX",
        spec_version=spec_version,
        generated=timestamp,
    )


def _cyclonedx_xml_spec_version(root_tag: str) -> str | None:
    """Extract ``1.6`` from a namespaced ``{http://cyclonedx.org/schema/bom/1.6}bom`` tag."""
    if "}" not in root_tag:
        return None
    namespace = root_tag[1:].split("}", 1)[0]
    return namespace.rsplit("/", 1)[-1] or None


def _cyclonedx_xml_vcs_url(external_refs_el: ElementTree.Element) -> str | None:
    """Read the VCS reference URL from a CycloneDX XML ``<externalReferences>`` node."""
    for ref in external_refs_el:
        if _local(ref.tag) != "reference" or ref.get("type") != "vcs":
            continue
        for node in ref:
            if _local(node.tag) == "url" and node.text:
                return node.text.strip()
    return None


def _cyclonedx_xml_properties(properties_el: ElementTree.Element) -> dict[str, str]:
    """Collect ``name → value`` pairs from a CycloneDX XML ``<properties>`` node."""
    props: dict[str, str] = {}
    for node in properties_el:
        if _local(node.tag) == "property":
            name = node.get("name")
            if name and node.text:
                props[name] = node.text.strip()
    return props


def _metadata_from_spdx_json(text: str) -> dict[str, Any]:
    doc = json.loads(text)
    root_pkg = _spdx_root_package(doc)
    application_id: str | None = None
    repository_url: str | None = None
    source_branch: str | None = None
    if root_pkg is not None:
        repository_url = _spdx_vcs_url(root_pkg.get("externalRefs"))
        provenance = _spdx_comment_provenance(root_pkg.get("comment"))
        application_id = provenance.get("application:id")
        source_branch = provenance.get("vcs:branch")
    spec_version = doc.get("spdxVersion")
    if isinstance(spec_version, str):
        spec_version = spec_version.removeprefix("SPDX-")
    created = (doc.get("creationInfo") or {}).get("created")
    return _metadata(
        component_name=doc.get("name"),
        application_id=application_id,
        repository_url=repository_url,
        source_branch=source_branch,
        format="SPDX",
        spec_version=spec_version,
        generated=created,
    )


def _spdx_root_package(doc: dict[str, Any]) -> dict[str, Any] | None:
    """Return the root application package that carries the provenance (Story 8.11)."""
    for pkg in doc.get("packages", []) or []:
        if isinstance(pkg, dict) and pkg.get("primaryPackagePurpose") == "APPLICATION":
            return pkg
    return None


def _spdx_vcs_url(external_refs: Any) -> str | None:
    if not isinstance(external_refs, list):
        return None
    for ref in external_refs:
        if isinstance(ref, dict) and ref.get("referenceType") == "vcs":
            return str(ref.get("referenceLocator", "")) or None
    return None


def _spdx_comment_provenance(comment: Any) -> dict[str, str]:
    """Parse ``application:id=...; vcs:branch=...`` from an SPDX package comment."""
    result: dict[str, str] = {}
    if not isinstance(comment, str):
        return result
    for part in comment.split(";"):
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if key and value:
            result[key] = value
    return result


def _ecosystem_from_purl(purl: str | None) -> str:
    """Derive the ecosystem from a ``pkg:<type>/...`` purl, defaulting to ``pypi`` (Story 8.26).

    Lets the ecosystem round-trip for older stored documents that predate the explicit
    ``package:ecosystem`` property (graceful default, AC #4).
    """
    if purl and purl.startswith("pkg:") and "/" in purl:
        purl_type = purl[len("pkg:") :].split("/", 1)[0]
        if purl_type:
            return purl_type
    return PYPI


def _component(
    name: str,
    version: str,
    type_: str | None,
    purl: str | None,
    license_: str | None,
    relationship: str | None = None,
    ecosystem: str | None = None,
) -> dict[str, Any]:
    resolved_purl = purl or None
    return {
        "name": name,
        "version": version,
        "type": (type_ or "").lower() or None,
        "purl": resolved_purl,
        "license": license_ or None,
        "relationship": relationship or None,  # direct | transitive | unknown (Story 8.4)
        # Ecosystem from the package:ecosystem property, falling back to the purl type (Story 8.26).
        "ecosystem": ecosystem or _ecosystem_from_purl(resolved_purl),
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
                relationship=_cyclonedx_property(comp.get("properties"), "sbom:relationship"),
                ecosystem=_cyclonedx_property(comp.get("properties"), "package:ecosystem"),
            )
        )
    return components


def _cyclonedx_property(properties: Any, name: str) -> str | None:
    """Read a named property value from a CycloneDX component (Story 8.4/8.26)."""
    if not isinstance(properties, list):
        return None
    for prop in properties:
        if isinstance(prop, dict) and prop.get("name") == name:
            return str(prop.get("value")) or None
    return None


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
        relationship: str | None = None
        ecosystem: str | None = None
        for child in element:
            local = _local(child.tag)
            if local in ("name", "version") and child.text:
                fields[local] = child.text.strip()
            elif local == "purl" and child.text:
                purl = child.text.strip()
            elif local == "licenses":
                license_parts.extend(_cyclonedx_xml_licenses(child))
            elif local == "properties":
                relationship = _cyclonedx_xml_property(child, "sbom:relationship") or relationship
                ecosystem = _cyclonedx_xml_property(child, "package:ecosystem") or ecosystem
        components.append(
            _component(
                name=fields.get("name", ""),
                version=fields.get("version", ""),
                type_=element.get("type"),
                purl=purl,
                license_=", ".join(license_parts) or None,
                relationship=relationship,
                ecosystem=ecosystem,
            )
        )
    return components


def _cyclonedx_xml_property(properties_el: ElementTree.Element, name: str) -> str | None:
    """Read a named property value from a CycloneDX XML component (Story 8.4/8.26)."""
    for node in properties_el.iter():
        if _local(node.tag) == "property" and node.get("name") == name and node.text:
            return node.text.strip()
    return None


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
    # Direct = SPDXIDs that are the target of a root DEPENDS_ON relationship (Story 8.4).
    # When no DEPENDS_ON edges exist (all-unknown, e.g. pixi.lock) leave relationship unset.
    relationships = doc.get("relationships", []) or []
    direct_ids = {
        r.get("relatedSpdxElement")
        for r in relationships
        if isinstance(r, dict) and r.get("relationshipType") == "DEPENDS_ON"
    }
    components = []
    for pkg in doc.get("packages", []) or []:
        relationship: str | None = None
        # Skip the root application package (version NOASSERTION) — it's not a dependency.
        if direct_ids and pkg.get("versionInfo") != "NOASSERTION":
            relationship = "direct" if pkg.get("SPDXID") in direct_ids else "transitive"
        components.append(
            _component(
                name=str(pkg.get("name", "")),
                version=str(pkg.get("versionInfo", "")),
                type_=pkg.get("primaryPackagePurpose"),
                purl=_spdx_purl(pkg.get("externalRefs")),
                license_=_spdx_license(pkg),
                relationship=relationship,
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
