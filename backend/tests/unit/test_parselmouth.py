"""Tests for the parselmouth conda↔PyPI name mapping (Story 8.10)."""

import json

import pytest
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
