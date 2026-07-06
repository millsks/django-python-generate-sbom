"""Tests for the license classification service (Story 4.3). No real network."""

from datetime import timedelta

import responses

from generate_sbom.analysis.services import http
from generate_sbom.analysis.services import license as license_service
from generate_sbom.sbom.parsers import PackageSpec


def _session() -> http.CachedLimiterSession:
    return http.build_session("test-pypi", timedelta(hours=1), 5)


def _pkg(name: str) -> PackageSpec:
    return PackageSpec(name=name, version="1.0")


def _mock_pypi(name: str, *, info: dict) -> None:
    responses.add(responses.GET, f"{license_service.PYPI_JSON_URL}/{name}/1.0/json", json={"info": info}, status=200)


CLASSIFIER = {
    "gpl": "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "lgpl": "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
    "mit": "License :: OSI Approved :: MIT License",
}


@responses.activate
def test_classify_places_packages_in_correct_tiers_and_order() -> None:
    _mock_pypi("gpl-pkg", info={"classifiers": [CLASSIFIER["gpl"]]})
    _mock_pypi("lgpl-pkg", info={"classifiers": [CLASSIFIER["lgpl"]]})
    _mock_pypi("mit-pkg", info={"classifiers": [CLASSIFIER["mit"]]})
    _mock_pypi("mystery-pkg", info={"license": "", "classifiers": []})  # no license → Unknown
    _mock_pypi("weird-pkg", info={"license_expression": "Proprietary-Weird"})  # non-SPDX → Unknown

    report = license_service.classify(
        [_pkg("gpl-pkg"), _pkg("lgpl-pkg"), _pkg("mit-pkg"), _pkg("mystery-pkg"), _pkg("weird-pkg")],
        session=_session(),
    )

    # Descending attention order (AC #3).
    assert [t["tier"] for t in report["tiers"]] == ["Strong Copyleft", "Weak Copyleft", "Unknown", "Permissive"]
    by_tier = {t["tier"]: t["packages"] for t in report["tiers"]}
    assert [p["name"] for p in by_tier["Strong Copyleft"]] == ["gpl-pkg"]
    assert by_tier["Strong Copyleft"][0]["license"] == "GPL-3.0-only"
    assert [p["name"] for p in by_tier["Weak Copyleft"]] == ["lgpl-pkg"]
    assert [p["name"] for p in by_tier["Permissive"]] == ["mit-pkg"]
    assert {p["name"] for p in by_tier["Unknown"]} == {"mystery-pkg", "weird-pkg"}
    assert report["summary"] == {
        "Strong Copyleft": 1,
        "Weak Copyleft": 1,
        "Unknown": 2,
        "Permissive": 1,
    }


@responses.activate
def test_license_expression_and_families() -> None:
    _mock_pypi("apache-pkg", info={"license_expression": "Apache-2.0"})
    _mock_pypi("agpl-pkg", info={"license_expression": "AGPL-3.0-only"})
    _mock_pypi("mpl-pkg", info={"license_expression": "MPL-2.0"})

    report = license_service.classify([_pkg("apache-pkg"), _pkg("agpl-pkg"), _pkg("mpl-pkg")], session=_session())

    by_tier = {t["tier"]: [p["name"] for p in t["packages"]] for t in report["tiers"]}
    assert by_tier["Permissive"] == ["apache-pkg"]
    assert by_tier["Strong Copyleft"] == ["agpl-pkg"]
    assert by_tier["Weak Copyleft"] == ["mpl-pkg"]


@responses.activate
def test_build_license_map_matches_phase5_normalization() -> None:
    """The shared resolver yields the same SPDX values Phase 5 records — no divergence (Story 8.25)."""
    _mock_pypi("mit-pkg", info={"classifiers": [CLASSIFIER["mit"]]})
    _mock_pypi("apache-pkg", info={"license_expression": "Apache-2.0"})
    responses.add(responses.GET, f"{license_service.PYPI_JSON_URL}/down-pkg/1.0/json", status=503)
    packages = [_pkg("mit-pkg"), _pkg("apache-pkg"), _pkg("down-pkg")]
    session = _session()

    license_map = license_service.build_license_map(packages, session=session)

    assert license_map == {("mit-pkg", "1.0"): "MIT", ("apache-pkg", "1.0"): "Apache-2.0", ("down-pkg", "1.0"): None}
    # Parity guard: the same values Phase 5's classify report derives from _extract_license (AC #4).
    report = license_service.classify(packages, session=session)
    reported = {p["name"]: p["license"] for tier in report["tiers"] for p in tier["packages"]}
    assert reported == {"mit-pkg": "MIT", "apache-pkg": "Apache-2.0", "down-pkg": "UNKNOWN"}


@responses.activate
def test_pypi_failure_degrades_to_unknown() -> None:
    responses.add(responses.GET, f"{license_service.PYPI_JSON_URL}/down-pkg/1.0/json", status=503)

    report = license_service.classify([_pkg("down-pkg")], session=_session())

    unknown = next(t for t in report["tiers"] if t["tier"] == "Unknown")
    assert [p["name"] for p in unknown["packages"]] == ["down-pkg"]
    assert unknown["packages"][0]["license"] == "UNKNOWN"
