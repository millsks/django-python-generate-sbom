"""Tests for the version-currency service (Story 4.5). No real network (responses)."""

from datetime import date, timedelta

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


def _mock_eol(product: str, cycles: object) -> None:
    responses.add(responses.GET, f"{versions_service.EOL_API_URL}/{product}.json", json=cycles, status=200)


def _mock_eol_missing(product: str) -> None:
    responses.add(responses.GET, f"{versions_service.EOL_API_URL}/{product}.json", status=404)


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
    report = versions_service.classify(packages, session=_session(), eol_session=_session(), lts_registry={})

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
    report = versions_service.classify(
        [PackageSpec(name="pkg", version="5.1.0")], session=_session(), eol_session=_session(), lts_registry={}
    )
    assert report["packages"][0]["currency"] == "behind-2+"


@responses.activate
def test_ahead_of_latest_is_current() -> None:
    _mock_latest("pkg", "1.0.0")  # installed newer than "latest" → current
    report = versions_service.classify(
        [PackageSpec(name="pkg", version="2.0.0")], session=_session(), eol_session=_session(), lts_registry={}
    )
    assert report["packages"][0]["currency"] == "current"


@responses.activate
def test_report_includes_package_ecosystem() -> None:
    _mock_latest("numpy", "1.26.4")
    report = versions_service.classify(
        [PackageSpec(name="numpy", version="1.26.0", ecosystem="conda")],
        session=_session(),
        eol_session=_session(),
        lts_registry={},
    )
    assert report["packages"][0]["ecosystem"] == "conda"


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
    # No registry entry and no endoflife.date data → on_lts is None (untracked, not "no").
    _mock_latest("pkg", "1.0.0")
    _mock_eol_missing("pkg")
    report = versions_service.classify(
        [PackageSpec(name="pkg", version="1.0.0")], session=_session(), eol_session=_session(), lts_registry={}
    )
    entry = report["packages"][0]
    assert entry["lts"] is None
    assert entry["on_lts"] is None


@responses.activate
def test_eol_lts_series_from_endoflife_date() -> None:
    # No registry entry, but endoflife.date tracks the project → derive its LTS series.
    _mock_latest("django", "5.2.0")
    _mock_eol(
        "django",
        [
            {"cycle": "5.2", "lts": False},
            {"cycle": "4.2", "lts": "2023-04-03"},  # date-form LTS
            {"cycle": "3.2", "lts": True},  # boolean-form LTS, older
        ],
    )
    report = versions_service.classify(
        [PackageSpec(name="django", version="4.2.11")], session=_session(), eol_session=_session(), lts_registry={}
    )
    entry = report["packages"][0]
    assert entry["lts"] == "4.2"  # latest LTS cycle, not 3.2
    assert entry["on_lts"] is True
    assert entry["currency"] == "current"


@responses.activate
def test_registry_overrides_endoflife_date() -> None:
    # An explicit registry entry wins over the API-derived series (operator authority).
    _mock_latest("django", "5.2.0")
    _mock_eol("django", [{"cycle": "4.2", "lts": True}])
    report = versions_service.classify(
        [PackageSpec(name="django", version="3.2.0")],
        session=_session(),
        eol_session=_session(),
        lts_registry={"django": "3.2"},
    )
    entry = report["packages"][0]
    assert entry["lts"] == "3.2"  # registry value, not endoflife.date's 4.2
    assert entry["on_lts"] is True


@responses.activate
def test_endoflife_date_error_falls_through_to_untracked() -> None:
    # endoflife.date unreachable / non-list body → untracked, never a fabricated LTS.
    _mock_latest("pkg", "2.0.0")
    responses.add(responses.GET, f"{versions_service.EOL_API_URL}/pkg.json", status=503)
    report = versions_service.classify(
        [PackageSpec(name="pkg", version="1.0.0")], session=_session(), eol_session=_session(), lts_registry={}
    )
    assert report["packages"][0]["lts"] is None


@responses.activate
def test_eol_product_name_mapping() -> None:
    # A package whose slug differs from its PyPI name resolves via _EOL_PRODUCTS.
    _mock_latest("opensearch-py", "2.0.0")
    _mock_eol("opensearch", [{"cycle": "2.11", "lts": True}])
    report = versions_service.classify(
        [PackageSpec(name="opensearch-py", version="2.11.0")],
        session=_session(),
        eol_session=_session(),
        lts_registry={},
    )
    assert report["packages"][0]["lts"] == "2.11"


@responses.activate
def test_pypi_failure_is_unknown() -> None:
    responses.add(responses.GET, f"{versions_service.PYPI_JSON_URL}/down-pkg/json", status=503)
    report = versions_service.classify(
        [PackageSpec(name="down-pkg", version="1.0.0")], session=_session(), eol_session=_session(), lts_registry={}
    )
    assert report["packages"][0]["currency"] == "unknown"


@responses.activate
def test_unparseable_versions_are_unknown() -> None:
    _mock_latest("weird-pkg", "not-a-version")
    report = versions_service.classify(
        [PackageSpec(name="weird-pkg", version="also-bad")], session=_session(), eol_session=_session(), lts_registry={}
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


# --- EOL-aware current-LTS selection (Story 8.7) -------------------------------------

_TODAY = date(2026, 7, 4)


@responses.activate
def test_expired_lts_points_to_current_lts() -> None:
    # Django 4.2 reached EOL 2026-04-07; on 2026-07-04 the current LTS is 5.2.
    _mock_latest("django", "5.2.0")
    _mock_eol(
        "django",
        [
            {"cycle": "5.2", "lts": True, "eol": "2028-04-30"},
            {"cycle": "4.2", "lts": True, "eol": "2026-04-07"},  # past EOL
        ],
    )
    report = versions_service.classify(
        [PackageSpec(name="django", version="4.2.30")],
        session=_session(),
        eol_session=_session(),
        lts_registry={},
        today=_TODAY,
    )
    entry = report["packages"][0]
    assert entry["lts"] == "5.2"  # current LTS, not the expired 4.2
    assert entry["on_lts"] is False  # installed 4.2.x is no longer on an active LTS
    assert entry["currency"] == "behind-2+"  # flagged as needing an upgrade


@responses.activate
def test_builtin_default_no_longer_traps_django() -> None:
    # Even though _DEFAULT_LTS pins django=4.2, endoflife.date's current LTS wins.
    _mock_latest("django", "5.2.0")
    _mock_eol("django", [{"cycle": "5.2", "lts": True, "eol": "2028-04-30"}])
    report = versions_service.classify(
        [PackageSpec(name="django", version="5.2.1")],
        session=_session(),
        eol_session=_session(),
        lts_registry={},
        today=_TODAY,
    )
    entry = report["packages"][0]
    assert entry["lts"] == "5.2"  # not the built-in 4.2
    assert entry["on_lts"] is True


@responses.activate
def test_all_lts_past_eol_degrades_to_highest_cycle() -> None:
    _mock_latest("legacy", "3.0.0")
    _mock_eol(
        "legacy",
        [
            {"cycle": "2.0", "lts": True, "eol": "2020-01-01"},
            {"cycle": "1.0", "lts": True, "eol": "2018-01-01"},
        ],
    )
    report = versions_service.classify(
        [PackageSpec(name="legacy", version="2.0.1")],
        session=_session(),
        eol_session=_session(),
        lts_registry={},
        today=_TODAY,
    )
    assert report["packages"][0]["lts"] == "2.0"  # highest cycle, not None / crash


@responses.activate
def test_missing_or_malformed_eol_is_treated_as_not_expired() -> None:
    _mock_latest("proj", "9.0.0")
    _mock_eol(
        "proj",
        [
            {"cycle": "8.0", "lts": True},  # no eol field
            {"cycle": "7.0", "lts": True, "eol": "n/a"},  # malformed
            {"cycle": "6.0", "lts": True, "eol": "2019-01-01"},  # expired
        ],
    )
    report = versions_service.classify(
        [PackageSpec(name="proj", version="8.0.0")],
        session=_session(),
        eol_session=_session(),
        lts_registry={},
        today=_TODAY,
    )
    assert report["packages"][0]["lts"] == "8.0"  # highest not-expired (missing eol)


@responses.activate
def test_operator_override_wins_over_current_lts() -> None:
    _mock_latest("django", "5.2.0")
    _mock_eol("django", [{"cycle": "5.2", "lts": True, "eol": "2028-04-30"}])
    report = versions_service.classify(
        [PackageSpec(name="django", version="4.2.0")],
        session=_session(),
        eol_session=_session(),
        lts_registry={"django": "4.2"},  # operator pin
        today=_TODAY,
    )
    entry = report["packages"][0]
    assert entry["lts"] == "4.2"  # operator override beats endoflife.date's 5.2
    assert entry["on_lts"] is True


@responses.activate
def test_python_falls_back_to_builtin_default() -> None:
    # endoflife.date tracks python but marks no cycle LTS → built-in 3.12 fallback (AC #4).
    _mock_latest("python", "3.13.0")
    _mock_eol(
        "python",
        [
            {"cycle": "3.13", "lts": False, "eol": "2029-10-01"},
            {"cycle": "3.12", "lts": False, "eol": "2028-10-01"},
        ],
    )
    report = versions_service.classify(
        [PackageSpec(name="python", version="3.12.4")],
        session=_session(),
        eol_session=_session(),
        lts_registry={},
        today=_TODAY,
    )
    entry = report["packages"][0]
    assert entry["lts"] == "3.12"  # built-in default, endoflife.date has no LTS cycle
    assert entry["on_lts"] is True
