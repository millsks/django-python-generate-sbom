"""conda↔PyPI name mapping via parselmouth (Story 8.10, 8.24).

conda-forge package names often differ from their PyPI names (e.g. conda
``pytorch`` ↔ PyPI ``torch``). parselmouth's ``compressed_mapping.json`` maps
conda-forge name → PyPI name; we load it (from a **bundled snapshot** so lookups
work on a fresh stack, overlaid by a **locally-stored** copy refreshed weekly by a
Celery beat task), invert it for PyPI → conda resolution, and fall back to the same
name when unmapped (graceful degradation).

Some PyPI names have **more than one** conda candidate (~1.5%, e.g. PyPI ``build``
→ conda ``build`` *and* ``python-build``). The bulk name→name map can't tell which
conda package actually *is* the PyPI project, so for those ambiguous names we
consult parselmouth's authoritative per-package data
(``pypi-to-conda-v1/conda-forge/<name>.json``, Story 8.24) and take the conda name
of the latest release. Curated overrides stay the highest-precedence authority.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from . import http

MAPPING_KEY = "parselmouth/compressed_mapping.json"

# Bundled conda→PyPI snapshot (gzipped), loaded as the baseline so lookups resolve
# correctly on a fresh stack before the weekly refresh populates storage (Story 8.24).
_BUNDLED_MAPPING = Path(__file__).resolve().parent / "data" / "compressed_mapping.json.gz"

# Built-in seed of common conda-forge → PyPI renames, used before the full map loads.
_SEED_CONDA_TO_PYPI: dict[str, str] = {
    "pytorch": "torch",
    "tensorflow-gpu": "tensorflow",
    "faiss-gpu": "faiss",
}

# Curated PyPI → conda-forge overrides (canonical PyPI name → conda-forge name), applied
# with highest precedence in ``pypi_to_conda``. Needed where the inverted map is
# ambiguous because a coincidentally same-named conda-forge package is a *different*
# project: e.g. PyPI ``build`` maps to conda-forge ``python-build`` — conda-forge's own
# ``build`` package is unrelated. Extend as such cases are found.
_PYPI_TO_CONDA_OVERRIDES: dict[str, str] = {
    "build": "python-build",
}

_conda_to_pypi: dict[str, str] | None = None  # canonical conda name → original PyPI name
_pypi_to_conda: dict[str, str] | None = None  # canonical PyPI name → original conda name
_ambiguous: set[str] | None = None  # canonical PyPI names with >1 conda candidate


def _load_bundled() -> dict[str, str]:
    """Read the bundled conda→pypi snapshot (gzip), or {} if absent/invalid."""
    try:
        with gzip.open(_BUNDLED_MAPPING, "rt", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


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
    global _conda_to_pypi, _pypi_to_conda, _ambiguous
    if _conda_to_pypi is not None:
        return
    # Baseline from the bundled snapshot so a fresh stack resolves correctly before the
    # weekly refresh; the stored copy (when present) takes precedence over the snapshot.
    raw = {**_SEED_CONDA_TO_PYPI, **_load_bundled(), **_load_stored()}
    conda_to_pypi: dict[str, str] = {}
    pypi_to_conda: dict[str, str] = {}
    candidate_counts: dict[str, int] = {}
    for conda_name, pypi_name in raw.items():
        if not pypi_name:  # conda-only package (no PyPI counterpart); e.g. conda ``xxhash``
            continue
        conda_key = canonicalize_name(str(conda_name))
        pypi_key = canonicalize_name(str(pypi_name))
        conda_to_pypi[conda_key] = str(pypi_name)
        candidate_counts[pypi_key] = candidate_counts.get(pypi_key, 0) + 1
        # Invert conda→pypi to pypi→conda, first mapping wins. Ambiguous names (>1
        # candidate) are resolved authoritatively by the per-package lookup / overrides
        # in ``pypi_to_conda``; here we just keep a deterministic first-candidate fallback.
        if pypi_key not in pypi_to_conda:
            pypi_to_conda[pypi_key] = str(conda_name)
    _conda_to_pypi, _pypi_to_conda = conda_to_pypi, pypi_to_conda
    _ambiguous = {key for key, count in candidate_counts.items() if count > 1}


def _latest_conda_name(conda_versions: dict[str, str]) -> str | None:
    """Return the conda name for the newest parseable PyPI version, or None."""
    best_key: str | None = None
    best_version: Version | None = None
    for version_str in conda_versions:
        try:
            version = Version(version_str)
        except InvalidVersion:
            continue
        if best_version is None or version > best_version:
            best_version, best_key = version, version_str
    return conda_versions.get(best_key) if best_key is not None else None


def _resolve_ambiguous(pypi_name: str) -> str | None:
    """Authoritatively resolve an ambiguous PyPI name via parselmouth's per-package data.

    Returns the conda-forge name for the latest release, or None on any failure (the
    caller then falls back to the bulk map / same name — never raises).
    """
    base = settings.PARSELMOUTH_PYPI_TO_CONDA_URL.rstrip("/")
    url = f"{base}/{canonicalize_name(pypi_name)}.json"
    try:
        response = http.parselmouth_session().get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    conda_versions = data.get("conda_versions")
    if not isinstance(conda_versions, dict) or not conda_versions:
        return None
    return _latest_conda_name({str(key): str(value) for key, value in conda_versions.items()})


def pypi_to_conda(name: str) -> str:
    """Return the conda-forge package name for a PyPI name (same name if unmapped).

    Precedence: curated override > authoritative per-package lookup (only for
    ambiguous names) > inverted bulk map > the same name.
    """
    _ensure_loaded()
    assert _pypi_to_conda is not None
    assert _ambiguous is not None
    key = canonicalize_name(name)
    if key in _PYPI_TO_CONDA_OVERRIDES:
        return _PYPI_TO_CONDA_OVERRIDES[key]
    if key in _ambiguous and settings.PARSELMOUTH_PYPI_TO_CONDA_URL:
        resolved = _resolve_ambiguous(name)
        if resolved:
            return resolved
    return _pypi_to_conda.get(key, name)


def conda_to_pypi(name: str) -> str:
    """Return the PyPI package name for a conda-forge name (same name if unmapped)."""
    _ensure_loaded()
    assert _conda_to_pypi is not None
    return _conda_to_pypi.get(canonicalize_name(name), name)


def _invalidate() -> None:
    global _conda_to_pypi, _pypi_to_conda, _ambiguous
    _conda_to_pypi = _pypi_to_conda = _ambiguous = None


def refresh_mapping() -> int:
    """Fetch parselmouth's mapping and store it locally; return the entry count.

    Called by the scheduled refresh task. Errors propagate to the caller (the task
    logs them); lookups keep using the previous copy / bundled snapshot until a
    refresh succeeds.
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
