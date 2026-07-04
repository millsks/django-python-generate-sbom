"""Tests for the dependency-graph service (Story 4.4). No real network (responses)."""

from datetime import timedelta

import responses

from generate_sbom.analysis.services import graph, http
from generate_sbom.sbom.parsers import PackageSpec

PKGS = [
    PackageSpec(name="requests", version="2.32.3"),
    PackageSpec(name="urllib3", version="2.3.0"),
    PackageSpec(name="certifi", version="2024.2.2"),
]


def _session() -> http.CachedLimiterSession:
    return http.build_session("test-graph", timedelta(hours=1), 5)


def _mock(name: str, version: str, requires: list[str] | None) -> None:
    responses.add(
        responses.GET,
        f"{graph.PYPI_JSON_URL}/{name}/{version}/json",
        json={"info": {"requires_dist": requires}},
        status=200,
    )


@responses.activate
def test_build_produces_cytoscape_json_and_svg() -> None:
    _mock(
        "requests",
        "2.32.3",
        [
            "urllib3<3,>=1.21.1",
            "certifi>=2017.4.17",
            "charset-normalizer<4,>=2",  # not in the resolved set → no edge
            "PySocks!=1.5.7,>=1.5.6; extra == 'socks'",  # extras-gated → skipped
        ],
    )
    _mock("urllib3", "2.3.0", [])
    _mock("certifi", "2024.2.2", None)

    cytoscape, svg = graph.build(PKGS, session=_session())

    # Exact Cytoscape shape with id = name==version (AD-9).
    node_ids = {n["data"]["id"] for n in cytoscape["nodes"]}
    assert node_ids == {"requests==2.32.3", "urllib3==2.3.0", "certifi==2024.2.2"}
    a_node = next(n for n in cytoscape["nodes"] if n["data"]["id"] == "requests==2.32.3")
    assert a_node["data"] == {"id": "requests==2.32.3", "label": "requests", "version": "2.32.3"}

    edges = {(e["data"]["source"], e["data"]["target"]) for e in cytoscape["edges"]}
    assert edges == {("requests==2.32.3", "urllib3==2.3.0"), ("requests==2.32.3", "certifi==2024.2.2")}

    # A real Graphviz SVG — not PyVis HTML (AD-9).
    assert svg.startswith(b"<?xml")
    assert b"<svg" in svg
    assert b"<html" not in svg.lower()


@responses.activate
def test_build_degrades_when_pypi_fails() -> None:
    responses.add(responses.GET, f"{graph.PYPI_JSON_URL}/requests/2.32.3/json", status=503)
    _mock("urllib3", "2.3.0", [])
    _mock("certifi", "2024.2.2", [])

    cytoscape, _svg = graph.build(PKGS, session=_session())

    assert len(cytoscape["nodes"]) == 3  # all nodes still present
    assert cytoscape["edges"] == []  # requests' deps couldn't be fetched → no edges
