"""Dependency-graph report service (Phase 6) — pure functions (AD-3, AD-9).

Builds a NetworkX ``DiGraph`` over the resolved packages, deriving ``depends-on``
edges from each package's PyPI ``requires_dist`` (the resolved list itself carries
no edges). Produces two outputs: the exact Cytoscape.js ``{nodes, edges}`` JSON
(served straight to the SPA — never PyVis HTML, AD-9) and a Graphviz SVG for
download.
"""

from __future__ import annotations

import re
from typing import Any

import networkx as nx
import requests
from packaging.requirements import InvalidRequirement, Requirement

from generate_sbom.sbom.parsers import PackageSpec

from . import http

PYPI_JSON_URL = "https://pypi.org/pypi"


def _normalize(name: str) -> str:
    """PEP 503 normalized distribution name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _node_id(name: str, version: str) -> str:
    return f"{name}=={version}"


def _requires(session: http.CachedLimiterSession, pkg: PackageSpec) -> list[str]:
    """Return the package's runtime dependency names (PyPI requires_dist), or [] on failure."""
    try:
        response = session.get(f"{PYPI_JSON_URL}/{pkg.name}/{pkg.version}/json")
        response.raise_for_status()
        requires_dist = response.json().get("info", {}).get("requires_dist") or []
    except (requests.RequestException, ValueError):
        return []
    names = []
    for raw in requires_dist:
        try:
            requirement = Requirement(raw)
        except InvalidRequirement:
            continue
        # Skip optional (extras-gated) dependencies; keep base runtime deps.
        if requirement.marker and "extra" in str(requirement.marker):
            continue
        names.append(_normalize(requirement.name))
    return names


def _to_cytoscape(digraph: nx.DiGraph) -> dict[str, Any]:
    """Convert the DiGraph to the exact Cytoscape.js data shape (AD-9)."""
    nodes = [
        {
            "data": {
                "id": node,
                "label": attrs["label"],
                "version": attrs["version"],
                "relationship": attrs.get("relationship"),  # direct | transitive | unknown (Story 8.5)
            }
        }
        for node, attrs in digraph.nodes(data=True)
    ]
    edges = [{"data": {"source": source, "target": target}} for source, target in digraph.edges()]
    return {"nodes": nodes, "edges": edges}


def _render_svg(digraph: nx.DiGraph) -> bytes:
    """Render the DiGraph to a Graphviz SVG (via pygraphviz)."""
    agraph = nx.nx_agraph.to_agraph(digraph)
    result: bytes = agraph.draw(format="svg", prog="dot")
    return result


def build(
    packages: list[PackageSpec], *, session: http.CachedLimiterSession | None = None
) -> tuple[dict[str, Any], bytes]:
    """Build the dependency graph; return (Cytoscape JSON, Graphviz SVG bytes) (FR-5.3)."""
    session = session or http.pypi_session()

    digraph: nx.DiGraph = nx.DiGraph()
    by_name: dict[str, str] = {}  # normalized name → node id
    for pkg in packages:
        node = _node_id(pkg.name, pkg.version)
        digraph.add_node(node, label=pkg.name, version=pkg.version, relationship=pkg.relationship)
        by_name[_normalize(pkg.name)] = node

    for pkg in packages:
        source = _node_id(pkg.name, pkg.version)
        for dep_name in _requires(session, pkg):
            target = by_name.get(dep_name)
            if target and target != source:
                digraph.add_edge(source, target)

    return _to_cytoscape(digraph), _render_svg(digraph)
