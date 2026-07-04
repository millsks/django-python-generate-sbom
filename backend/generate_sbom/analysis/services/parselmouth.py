"""conda↔PyPI name mapping via parselmouth (Story 8.10).

conda-forge package names often differ from their PyPI names (e.g. conda
``pytorch`` ↔ PyPI ``torch``). parselmouth's ``compressed_mapping.json`` maps
conda-forge name → PyPI name; we load a **locally-stored** copy (refreshed
periodically by a Celery beat task — never a per-package network lookup), invert
it for PyPI → conda resolution, and fall back to the same name when the map is
unavailable (graceful degradation). A small built-in seed covers common renames
before the first refresh.
"""

from __future__ import annotations

import json

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from packaging.utils import canonicalize_name

MAPPING_KEY = "parselmouth/compressed_mapping.json"

# Built-in seed of common conda-forge → PyPI renames, used before the first refresh
# populates the full map (graceful degradation).
_SEED_CONDA_TO_PYPI: dict[str, str] = {
    "pytorch": "torch",
    "tensorflow-gpu": "tensorflow",
    "faiss-gpu": "faiss",
}

_conda_to_pypi: dict[str, str] | None = None  # canonical conda name → original PyPI name
_pypi_to_conda: dict[str, str] | None = None  # canonical PyPI name → original conda name


def _load_stored() -> dict[str, str]:
    """Read the stored parselmouth mapping (conda → pypi), or {} if absent/invalid."""
    if not default_storage.exists(MAPPING_KEY):
        return {}
    try:
        with default_storage.open(MAPPING_KEY) as handle:
            data = json.loads(handle.read())
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _ensure_loaded() -> None:
    global _conda_to_pypi, _pypi_to_conda
    if _conda_to_pypi is not None:
        return
    raw = {**_SEED_CONDA_TO_PYPI, **_load_stored()}
    conda_to_pypi: dict[str, str] = {}
    pypi_to_conda: dict[str, str] = {}
    for conda_name, pypi_name in raw.items():
        if not pypi_name:  # conda-only package (no PyPI counterpart)
            continue
        conda_key = canonicalize_name(str(conda_name))
        pypi_key = canonicalize_name(str(pypi_name))
        conda_to_pypi[conda_key] = str(pypi_name)
        # Prefer an identity mapping (conda name == pypi name) when several exist.
        if pypi_key not in pypi_to_conda or conda_key == pypi_key:
            pypi_to_conda[pypi_key] = str(conda_name)
    _conda_to_pypi, _pypi_to_conda = conda_to_pypi, pypi_to_conda


def pypi_to_conda(name: str) -> str:
    """Return the conda-forge package name for a PyPI name (same name if unmapped)."""
    _ensure_loaded()
    assert _pypi_to_conda is not None
    return _pypi_to_conda.get(canonicalize_name(name), name)


def conda_to_pypi(name: str) -> str:
    """Return the PyPI package name for a conda-forge name (same name if unmapped)."""
    _ensure_loaded()
    assert _conda_to_pypi is not None
    return _conda_to_pypi.get(canonicalize_name(name), name)


def _invalidate() -> None:
    global _conda_to_pypi, _pypi_to_conda
    _conda_to_pypi = _pypi_to_conda = None


def refresh_mapping() -> int:
    """Fetch parselmouth's mapping and store it locally; return the entry count.

    Called by the scheduled refresh task. Errors propagate to the caller (the task
    logs them); lookups keep using the previous copy / seed until a refresh succeeds.
    """
    response = requests.get(settings.PARSELMOUTH_MAPPING_URL, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("parselmouth mapping is not a JSON object")
    if default_storage.exists(MAPPING_KEY):
        default_storage.delete(MAPPING_KEY)
    default_storage.save(MAPPING_KEY, ContentFile(json.dumps(data).encode("utf-8")))
    _invalidate()
    return len(data)
