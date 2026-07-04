"""Tests for the version-currency service (Story 4.5). No real network (responses)."""

from datetime import timedelta

import pytest
import responses

from generate_sbom.analysis.services import http
from generate_sbom.analysis.services import versions as versions_service
from generate_sbom.sbom.parsers import PackageSpec


def _session() -> http.CachedLimiterSession:
    return http.build_session("test-versions", timedelta(hours=1), 5)


def _mock_latest(name: str, latest: str | None) -> None:
    body = {"info": {"version": latest}} if latest is not None else {"info": {}}
    responses.add(responses.GET, f"{versions_service.PYPI_JSON_URL}/{name}/json", json=body, status=200)


@responses.activate
def test_currency_classes() -> None:
    _mock_latest("current-pkg", "5.2.5")  # installed 5.2.1 → same series → current
    _mock_latest("behind1-pkg", "5.2.0")  # installed 5.1.9 → one minor behind → behind-1
    _mock_latest("behind2-pkg", "5.2.0")  # installed 4.9.0 → major gap → behind-2+
    _mock_latest("unknown-pkg", None)  # no latest → unknown

    packages = [
        PackageSpec(name="current-pkg", version="5.2.1"),
        PackageSpec(name="behind1-pkg", version="5.1.9"),
        PackageSpec(name="behind2-pkg", version="4.9.0"),
        PackageSpec(name="unknown-pkg", version="1.0.0"),
    ]
    report = versions_service.classify(packages, session=_session(), lts_registry={})

    by_name = {e["name"]: e["currency"] for e in report["packages"]}
    assert by_name == {
        "current-pkg": "current",
        "behind1-pkg": "behind-1",
        "behind2-pkg": "behind-2+",
        "unknown-pkg": "unknown",
    }
    assert report["summary"] == {"current": 1, "behind-1": 1, "behind-2+": 1, "unknown": 1}


@responses.activate
def test_two_minor_behind_is_behind_2plus() -> None:
    _mock_latest("pkg", "5.3.0")  # installed 5.1.0 → two minors behind → behind-2+
    report = versions_service.classify([PackageSpec(name="pkg", version="5.1.0")], session=_session(), lts_registry={})
    assert report["packages"][0]["currency"] == "behind-2+"


@responses.activate
def test_ahead_of_latest_is_current() -> None:
    _mock_latest("pkg", "1.0.0")  # installed newer than "latest" → current
    report = versions_service.classify([PackageSpec(name="pkg", version="2.0.0")], session=_session(), lts_registry={})
    assert report["packages"][0]["currency"] == "current"


@responses.activate
def test_lts_series_counts_as_current() -> None:
    # Django 4.2 (an LTS) is behind latest 5.2, but on the LTS series → current.
    _mock_latest("django", "5.2.0")
    report = versions_service.classify(
        [PackageSpec(name="django", version="4.2.11")],
        session=_session(),
        lts_registry={"django": "4.2"},
    )
    entry = report["packages"][0]
    assert entry["currency"] == "current"
    assert entry["lts"] == "4.2"
    assert entry["on_lts"] is True


@responses.activate
def test_on_lts_flag_reflects_installed_series() -> None:
    # Same package, tracked LTS 4.2: on the LTS series → True; off it → False.
    _mock_latest("django", "5.2.0")
    report = versions_service.classify(
        [PackageSpec(name="django", version="5.1.0")],
        session=_session(),
        lts_registry={"django": "4.2"},
    )
    entry = report["packages"][0]
    assert entry["lts"] == "4.2"
    assert entry["on_lts"] is False


@responses.activate
def test_on_lts_is_none_when_untracked() -> None:
    # No LTS tracked for the package → on_lts is None (untracked, not a "no").
    _mock_latest("pkg", "1.0.0")
    report = versions_service.classify([PackageSpec(name="pkg", version="1.0.0")], session=_session(), lts_registry={})
    entry = report["packages"][0]
    assert entry["lts"] is None
    assert entry["on_lts"] is None


@responses.activate
def test_pypi_failure_is_unknown() -> None:
    responses.add(responses.GET, f"{versions_service.PYPI_JSON_URL}/down-pkg/json", status=503)
    report = versions_service.classify(
        [PackageSpec(name="down-pkg", version="1.0.0")], session=_session(), lts_registry={}
    )
    assert report["packages"][0]["currency"] == "unknown"


@responses.activate
def test_unparseable_versions_are_unknown() -> None:
    _mock_latest("weird-pkg", "not-a-version")
    report = versions_service.classify(
        [PackageSpec(name="weird-pkg", version="also-bad")], session=_session(), lts_registry={}
    )
    assert report["packages"][0]["currency"] == "unknown"


@responses.activate
def test_garbage_lts_is_ignored() -> None:
    _mock_latest("pkg", "5.2.0")  # installed 5.2.1 → current regardless of bad LTS entry
    report = versions_service.classify(
        [PackageSpec(name="pkg", version="5.2.1")], session=_session(), lts_registry={"pkg": "not-a-version"}
    )
    assert report["packages"][0]["currency"] == "current"


def test_malformed_registry_keeps_defaults(settings: pytest.FixtureRequest) -> None:
    settings.SBOM_LTS_REGISTRY = "this is not json {{"  # type: ignore[attr-defined]
    registry = versions_service.load_lts_registry()
    assert registry == {"django": "4.2", "python": "3.12"}


def test_load_lts_registry_defaults_and_override(settings: pytest.FixtureRequest) -> None:
    settings.SBOM_LTS_REGISTRY = ""  # type: ignore[attr-defined]
    defaults = versions_service.load_lts_registry()
    assert defaults["django"] == "4.2"
    assert defaults["python"] == "3.12"

    settings.SBOM_LTS_REGISTRY = '{"Django": "5.2", "numpy": "1.26"}'  # type: ignore[attr-defined]
    overridden = versions_service.load_lts_registry()
    assert overridden["django"] == "5.2"  # operator override (name normalized)
    assert overridden["numpy"] == "1.26"  # operator extension
    assert overridden["python"] == "3.12"  # default retained


def test_load_lts_registry_from_file(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    registry_file = tmp_path / "lts.json"  # type: ignore[operator]
    registry_file.write_text('{"flask": "3.0"}', encoding="utf-8")
    settings.SBOM_LTS_REGISTRY = str(registry_file)  # type: ignore[attr-defined]
    registry = versions_service.load_lts_registry()
    assert registry["flask"] == "3.0"
    assert registry["django"] == "4.2"  # defaults still present
