"""Tests for the parselmouth conda↔PyPI name mapping (Story 8.10, 8.24)."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests
import responses
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from generate_sbom.analysis.services import parselmouth


@pytest.fixture(autouse=True)
def _tmp_media_and_reset(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]
    parselmouth._invalidate()


def _store(mapping: dict[str, str | None]) -> None:
    if default_storage.exists(parselmouth.MAPPING_KEY):
        default_storage.delete(parselmouth.MAPPING_KEY)
    default_storage.save(parselmouth.MAPPING_KEY, ContentFile(json.dumps(mapping).encode("utf-8")))


def test_seed_maps_common_renames_before_refresh() -> None:
    # With no stored file, the built-in seed applies (conda pytorch ↔ pypi torch).
    assert parselmouth.conda_to_pypi("pytorch") == "torch"
    assert parselmouth.pypi_to_conda("torch") == "pytorch"


def test_same_name_fallback_when_unmapped() -> None:
    assert parselmouth.pypi_to_conda("requests") == "requests"
    assert parselmouth.conda_to_pypi("numpy") == "numpy"


def test_stored_mapping_is_used_and_inverted() -> None:
    _store({"my-conda-pkg": "my-pypi-pkg", "conda-only": None})
    parselmouth._invalidate()

    assert parselmouth.conda_to_pypi("my-conda-pkg") == "my-pypi-pkg"
    assert parselmouth.pypi_to_conda("my-pypi-pkg") == "my-conda-pkg"
    # A conda-only package (null PyPI name) isn't invertible → same-name fallback.
    assert parselmouth.pypi_to_conda("conda-only") == "conda-only"


def test_pypi_build_maps_to_python_build_override() -> None:
    # PyPI ``build``'s true conda-forge equivalent is ``python-build`` — the curated
    # override applies even with no stored map (conda-forge's own ``build`` is unrelated).
    assert parselmouth.pypi_to_conda("build") == "python-build"


def test_override_wins_over_stored_inverted_map() -> None:
    # Even when the stored map would invert ``build`` → conda ``build``, the override wins.
    _store({"build": "build"})
    parselmouth._invalidate()

    assert parselmouth.pypi_to_conda("build") == "python-build"
    # Forward direction is unaffected: conda ``build`` → pypi ``build``.
    assert parselmouth.conda_to_pypi("build") == "build"


def test_inversion_does_not_prefer_identity() -> None:
    # Two conda names map to one PyPI name; the identity (conda == pypi) is NOT preferred
    # anymore — first mapping wins. (Old behavior returned "shared-pypi".)
    _store({"first-conda": "shared-pypi", "shared-pypi": "shared-pypi"})
    parselmouth._invalidate()

    assert parselmouth.pypi_to_conda("shared-pypi") == "first-conda"


def test_normal_one_to_one_name_unaffected() -> None:
    # A 1:1 mapping still inverts cleanly; an unmapped name falls back to itself.
    _store({"numpy": "numpy"})
    parselmouth._invalidate()

    assert parselmouth.pypi_to_conda("numpy") == "numpy"
    assert parselmouth.pypi_to_conda("nonexistent-pkg") == "nonexistent-pkg"


@responses.activate
def test_refresh_fetches_stores_and_reloads(settings: pytest.FixtureRequest) -> None:
    settings.PARSELMOUTH_MAPPING_URL = "https://example.test/mapping.json"  # type: ignore[attr-defined]
    responses.add(responses.GET, "https://example.test/mapping.json", json={"a-conda": "a-pypi"}, status=200)

    count = parselmouth.refresh_mapping()

    assert count == 1
    assert default_storage.exists(parselmouth.MAPPING_KEY)
    assert parselmouth.conda_to_pypi("a-conda") == "a-pypi"  # refreshed map is live


@responses.activate
def test_refresh_rejects_non_object_body(settings: pytest.FixtureRequest) -> None:
    settings.PARSELMOUTH_MAPPING_URL = "https://example.test/mapping.json"  # type: ignore[attr-defined]
    responses.add(responses.GET, "https://example.test/mapping.json", json=["not", "a", "dict"], status=200)

    with pytest.raises(ValueError, match="not a JSON object"):
        parselmouth.refresh_mapping()


# --- Story 8.24: bundled snapshot + authoritative per-package disambiguation ---


def test_bundled_snapshot_resolves_unambiguous_name() -> None:
    # The committed snapshot ships real data, so a fresh stack (no stored map) resolves
    # PyPI xxhash → conda python-xxhash without waiting for the weekly refresh. xxhash is
    # unambiguous (python-xxhash → xxhash; conda xxhash → None is skipped).
    assert parselmouth.pypi_to_conda("xxhash") == "python-xxhash"


def test_latest_conda_name_picks_newest_version() -> None:
    versions = {"1.0.0": "old-conda", "2.1.0": "new-conda", "0.9": "older", "not-a-version": "skip"}
    assert parselmouth._latest_conda_name(versions) == "new-conda"
    assert parselmouth._latest_conda_name({}) is None


def test_ambiguous_name_resolved_via_per_package(settings: pytest.FixtureRequest) -> None:
    # Two conda names claim one PyPI name → ambiguous. With the per-package URL set, the
    # authoritative lookup decides it (latest release wins).
    settings.PARSELMOUTH_PYPI_TO_CONDA_URL = "https://map.test/pypi-to-conda-v1/conda-forge/"  # type: ignore[attr-defined]
    _store({"foo": "myambig", "foo-base": "myambig"})
    parselmouth._invalidate()

    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"conda_versions": {"1.0.0": "foo", "2.0.0": "foo-base"}}
    session = MagicMock()
    session.get.return_value = response

    with patch.object(parselmouth.http, "parselmouth_session", return_value=session):
        assert parselmouth.pypi_to_conda("myambig") == "foo-base"
    assert "myambig.json" in session.get.call_args.args[0]


def test_ambiguous_falls_back_to_bulk_when_per_package_fails(settings: pytest.FixtureRequest) -> None:
    settings.PARSELMOUTH_PYPI_TO_CONDA_URL = "https://map.test/pypi-to-conda-v1/conda-forge/"  # type: ignore[attr-defined]
    _store({"foo": "myambig", "foo-base": "myambig"})
    parselmouth._invalidate()

    session = MagicMock()
    session.get.side_effect = requests.RequestException("boom")
    with patch.object(parselmouth.http, "parselmouth_session", return_value=session):
        # Deterministic fallback to the bulk map's first candidate (first inserted).
        assert parselmouth.pypi_to_conda("myambig") == "foo"


def test_override_wins_over_per_package_lookup(settings: pytest.FixtureRequest) -> None:
    # ``build`` is both ambiguous and overridden; the override short-circuits — no network.
    settings.PARSELMOUTH_PYPI_TO_CONDA_URL = "https://map.test/pypi-to-conda-v1/conda-forge/"  # type: ignore[attr-defined]
    session = MagicMock()
    with patch.object(parselmouth.http, "parselmouth_session", return_value=session):
        assert parselmouth.pypi_to_conda("build") == "python-build"
    session.get.assert_not_called()


def test_per_package_disabled_by_empty_url_uses_bulk(settings: pytest.FixtureRequest) -> None:
    # With the URL empty (the test default), ambiguous names never hit the network.
    settings.PARSELMOUTH_PYPI_TO_CONDA_URL = ""  # type: ignore[attr-defined]
    _store({"foo": "myambig", "foo-base": "myambig"})
    parselmouth._invalidate()

    session = MagicMock()
    with patch.object(parselmouth.http, "parselmouth_session", return_value=session):
        assert parselmouth.pypi_to_conda("myambig") == "foo"
    session.get.assert_not_called()


@pytest.mark.parametrize("payload", [["not", "a", "dict"], {"format_version": "1.0"}, {"conda_versions": {}}])
def test_ambiguous_falls_back_on_malformed_per_package(settings: pytest.FixtureRequest, payload: object) -> None:
    # A per-package response that isn't a dict, or lacks/empties conda_versions, degrades
    # to the bulk map's first candidate rather than raising.
    settings.PARSELMOUTH_PYPI_TO_CONDA_URL = "https://map.test/pypi-to-conda-v1/conda-forge/"  # type: ignore[attr-defined]
    _store({"foo": "myambig", "foo-base": "myambig"})
    parselmouth._invalidate()

    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    session = MagicMock()
    session.get.return_value = response
    with patch.object(parselmouth.http, "parselmouth_session", return_value=session):
        assert parselmouth.pypi_to_conda("myambig") == "foo"


def test_latest_conda_name_none_when_no_parseable_versions() -> None:
    assert parselmouth._latest_conda_name({"bad": "x", "also-bad": "y"}) is None


def test_load_bundled_missing_file_returns_empty() -> None:
    with patch.object(parselmouth, "_BUNDLED_MAPPING", parselmouth.Path("/nonexistent/mapping.json.gz")):
        assert parselmouth._load_bundled() == {}


def test_parselmouth_session_is_a_cached_singleton() -> None:
    from generate_sbom.analysis.services import http

    session = http.parselmouth_session()
    assert isinstance(session, http.CachedLimiterSession)
    assert http.parselmouth_session() is session  # memoized
