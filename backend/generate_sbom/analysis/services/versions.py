"""Version-currency report service (Phase 7) — pure functions (AD-3).

Fetches the latest stable version of each package from the PyPI JSON API (via
``http.pypi_session``) and classifies currency by release-series distance, with
LTS-aware handling for registry-tracked packages. Returns a plain report dict.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import requests
from django.conf import settings
from packaging.version import InvalidVersion, Version

from generate_sbom.sbom.parsers import PackageSpec

from . import http

PYPI_JSON_URL = "https://pypi.org/pypi"

CURRENT = "current"
BEHIND_1 = "behind-1"
BEHIND_2 = "behind-2+"
UNKNOWN = "unknown"
CURRENCY_CLASSES = [CURRENT, BEHIND_1, BEHIND_2, UNKNOWN]

# Built-in LTS defaults; extended/overridden via SBOM_LTS_REGISTRY (FR-5.4).
_DEFAULT_LTS = {"django": "4.2", "python": "3.12"}


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_lts_registry() -> dict[str, str]:
    """Return the LTS registry: built-in defaults + SBOM_LTS_REGISTRY (file path or inline JSON)."""
    registry = {_normalize(name): version for name, version in _DEFAULT_LTS.items()}
    raw = (getattr(settings, "SBOM_LTS_REGISTRY", "") or "").strip()
    if not raw:
        return registry
    path = Path(raw)
    text = path.read_text(encoding="utf-8") if path.is_file() else raw
    try:
        overrides = json.loads(text)
    except (ValueError, OSError):
        return registry  # malformed → keep defaults
    if isinstance(overrides, dict):
        registry.update({_normalize(str(name)): str(version) for name, version in overrides.items()})
    return registry


def _latest_version(session: http.CachedLimiterSession, name: str) -> str | None:
    try:
        response = session.get(f"{PYPI_JSON_URL}/{name}/json")
        response.raise_for_status()
        version: str | None = response.json().get("info", {}).get("version")
    except (requests.RequestException, ValueError):
        return None
    return version


def _classify_currency(installed: str, latest: str | None, lts: str | None) -> str:
    """Classify currency into current / behind-1 / behind-2+ / unknown (FR-5.4)."""
    if latest is None:
        return UNKNOWN
    try:
        installed_v = Version(installed)
        latest_v = Version(latest)
    except InvalidVersion:
        return UNKNOWN

    # LTS-aware: being on the tracked LTS series counts as current.
    if lts:
        try:
            if installed_v.release[:2] == Version(lts).release[:2]:
                return CURRENT
        except InvalidVersion:
            pass

    if installed_v.release[:2] == latest_v.release[:2] or installed_v >= latest_v:
        return CURRENT
    if installed_v.major == latest_v.major:
        return BEHIND_1 if (latest_v.minor - installed_v.minor) == 1 else BEHIND_2
    return BEHIND_2  # major-version gap


def classify(
    packages: list[PackageSpec],
    *,
    session: http.CachedLimiterSession | None = None,
    lts_registry: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Classify each package's version currency and return the report dict (FR-5.4)."""
    session = session or http.pypi_session()
    registry = lts_registry if lts_registry is not None else load_lts_registry()

    entries: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for pkg in packages:
        latest = _latest_version(session, pkg.name)
        lts = registry.get(_normalize(pkg.name))
        currency = _classify_currency(pkg.version, latest, lts)
        counts[currency] += 1
        entries.append({"name": pkg.name, "installed": pkg.version, "latest": latest, "currency": currency, "lts": lts})

    return {"packages": entries, "summary": {klass: counts.get(klass, 0) for klass in CURRENCY_CLASSES}}
