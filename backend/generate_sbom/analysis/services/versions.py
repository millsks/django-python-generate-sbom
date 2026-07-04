"""Version-currency report service (Phase 7) — pure functions (AD-3).

Fetches the latest stable version of each package from the PyPI JSON API (via
``http.pypi_session``) and classifies currency by release-series distance, with
LTS-aware handling. Each package's LTS series is resolved by precedence (Story 8.7):
operator override (``SBOM_LTS_REGISTRY``) → endoflife.date's *current* LTS (the
highest LTS cycle whose ``eol`` is still in the future) → built-in ``_DEFAULT_LTS``
fallback; packages with no match stay untracked. Returns a plain report dict.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import requests
from django.conf import settings
from packaging.version import InvalidVersion, Version

from generate_sbom.sbom.parsers import PackageSpec

from . import http

PYPI_JSON_URL = "https://pypi.org/pypi"
EOL_API_URL = "https://endoflife.date/api"

CURRENT = "current"
BEHIND_1 = "behind-1"
BEHIND_2 = "behind-2+"
UNKNOWN = "unknown"
CURRENCY_CLASSES = [CURRENT, BEHIND_1, BEHIND_2, UNKNOWN]

# Built-in LTS defaults; extended/overridden via SBOM_LTS_REGISTRY (FR-5.4).
_DEFAULT_LTS = {"django": "4.2", "python": "3.12"}

# normalized package name → endoflife.date product slug, for the cases where they
# differ. Unmapped names try the normalized name directly and fall through to
# untracked on a 404 — never a wrong match.
_EOL_PRODUCTS = {
    "opensearch-py": "opensearch",
}


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# Built-in defaults, normalized; used only as a last-resort LTS fallback (Story 8.7).
_DEFAULT_LTS_NORMALIZED = {_normalize(name): version for name, version in _DEFAULT_LTS.items()}


def _eol_version_key(cycle: str) -> Version:
    """Sort key for endoflife.date cycle labels; unparseable cycles sort lowest."""
    try:
        return Version(cycle)
    except InvalidVersion:
        return Version("0")


def _parse_eol(value: object) -> date | None:
    """Parse an endoflife.date ``eol`` field to a date, or None if it's not a date.

    ``eol`` is normally an ISO ``YYYY-MM-DD`` string, but can be a boolean (``false``
    = no EOL scheduled) or absent. A non-date value means "no known EOL" → not expired.
    """
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _eol_lts_series(session: http.CachedLimiterSession, name: str, *, today: date | None = None) -> str | None:
    """Return the *currently-supported* LTS release series from endoflife.date, or None.

    endoflife.date's ``lts`` field is ``false`` (not LTS), ``true``, or the date LTS
    began — any truthy value marks an LTS cycle. Among LTS cycles, pick the highest
    whose ``eol`` is still in the future ("current LTS"); if every LTS cycle is already
    past EOL, degrade to the highest LTS cycle rather than crash or return None (Story
    8.7). A missing/malformed ``eol`` is treated as not-expired. Network/parse errors
    and untracked products fall through to None (no guess).
    """
    if today is None:
        today = datetime.now(UTC).date()
    product = _EOL_PRODUCTS.get(_normalize(name), _normalize(name))
    try:
        response = session.get(f"{EOL_API_URL}/{product}.json")
        response.raise_for_status()
        cycles = response.json()
    except (requests.RequestException, ValueError):
        return None
    if not isinstance(cycles, list):
        return None
    lts = [
        (str(c["cycle"]), _parse_eol(c.get("eol")))
        for c in cycles
        if isinstance(c, dict) and c.get("lts") and "cycle" in c
    ]
    if not lts:
        return None
    supported = [cycle for cycle, eol in lts if eol is None or eol >= today]
    pool = supported or [cycle for cycle, _ in lts]  # all past EOL → degrade to highest cycle
    return max(pool, key=_eol_version_key)


def load_operator_registry() -> dict[str, str]:
    """Return the operator LTS overrides from SBOM_LTS_REGISTRY only (no built-in defaults).

    This is the top-precedence layer (Story 8.1 AC #5): an explicit operator entry wins
    over the endoflife.date-derived series. Built-in ``_DEFAULT_LTS`` is a separate,
    last-resort fallback (Story 8.7) and is intentionally excluded here.
    """
    raw = (getattr(settings, "SBOM_LTS_REGISTRY", "") or "").strip()
    if not raw:
        return {}
    path = Path(raw)
    text = path.read_text(encoding="utf-8") if path.is_file() else raw
    try:
        overrides = json.loads(text)
    except (ValueError, OSError):
        return {}  # malformed → no operator overrides
    if isinstance(overrides, dict):
        return {_normalize(str(name)): str(version) for name, version in overrides.items()}
    return {}


def load_lts_registry() -> dict[str, str]:
    """Return built-in defaults merged with SBOM_LTS_REGISTRY (overrides win)."""
    return {**_DEFAULT_LTS_NORMALIZED, **load_operator_registry()}


def _latest_version(session: http.CachedLimiterSession, name: str) -> str | None:
    try:
        response = session.get(f"{PYPI_JSON_URL}/{name}/json")
        response.raise_for_status()
        version: str | None = response.json().get("info", {}).get("version")
    except (requests.RequestException, ValueError):
        return None
    return version


def _is_on_lts(installed: str, lts: str | None) -> bool | None:
    """Whether ``installed`` is on the tracked LTS release series.

    Returns ``None`` when no LTS is tracked for the package (untracked, not "no"),
    ``True`` when the installed major.minor matches the LTS series, else ``False``.
    """
    if not lts:
        return None
    try:
        return Version(installed).release[:2] == Version(lts).release[:2]
    except InvalidVersion:
        return None


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
    eol_session: http.CachedLimiterSession | None = None,
    lts_registry: dict[str, str] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Classify each package's version currency and return the report dict (FR-5.4).

    LTS precedence (Story 8.7): operator override (``SBOM_LTS_REGISTRY`` /
    ``lts_registry``) → endoflife.date current LTS → built-in ``_DEFAULT_LTS`` fallback.
    """
    session = session or http.pypi_session()
    eol = eol_session or http.eol_session()
    overrides = lts_registry if lts_registry is not None else load_operator_registry()
    today = today or datetime.now(UTC).date()

    entries: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for pkg in packages:
        latest = _latest_version(session, pkg.name)
        norm = _normalize(pkg.name)
        # Operator override wins; else the live current LTS; else the built-in default.
        lts = overrides.get(norm) or _eol_lts_series(eol, pkg.name, today=today) or _DEFAULT_LTS_NORMALIZED.get(norm)
        currency = _classify_currency(pkg.version, latest, lts)
        counts[currency] += 1
        entries.append(
            {
                "name": pkg.name,
                "installed": pkg.version,
                "latest": latest,
                "currency": currency,
                "lts": lts,
                "on_lts": _is_on_lts(pkg.version, lts),
                "ecosystem": pkg.ecosystem,
            }
        )

    return {"packages": entries, "summary": {klass: counts.get(klass, 0) for klass in CURRENCY_CLASSES}}
