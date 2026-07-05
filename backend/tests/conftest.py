"""Shared pytest fixtures for both unit and integration tests."""

from collections.abc import Iterator

import pytest

from generate_sbom.analysis.services import parselmouth


@pytest.fixture(autouse=True)
def _parselmouth_test_isolation(settings: pytest.FixtureRequest) -> Iterator[None]:
    """Isolate the parselmouth mapping per test and keep it offline.

    Story 8.24 added an authoritative per-package HTTP lookup for the ~1.5% of PyPI
    names with multiple conda candidates. Disabling that URL by default keeps unit
    tests deterministic and network-free (they fall back to the bundled bulk map);
    tests that exercise the lookup re-enable the URL and mock the response. Also
    resets the module-level cache so the bundled snapshot doesn't leak across tests.
    """
    settings.PARSELMOUTH_PYPI_TO_CONDA_URL = ""  # type: ignore[attr-defined]
    parselmouth._invalidate()
    yield
    parselmouth._invalidate()
