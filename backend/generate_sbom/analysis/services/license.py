"""License compliance report service (Phase 5) — pure functions (AD-3).

Extracts the declared license per package from PyPI JSON metadata (via
``http.pypi_session``) and classifies each into one of four legal-risk tiers
(FR-5.2). Returns a plain report dict; persistence/progress/envelope live in the
Phase 5 task.

Note: the resolved package set is not installed in this environment, so the
license source is the PyPI JSON API (PEP 639 ``license_expression`` → Trove
classifiers → free-text ``license``), not ``pip-licenses`` (which reads the
installed environment).
"""

from __future__ import annotations

from typing import Any

import requests

from generate_sbom.sbom.parsers import PackageSpec

from . import http

PYPI_JSON_URL = "https://pypi.org/pypi"

STRONG_COPYLEFT = "Strong Copyleft"
WEAK_COPYLEFT = "Weak Copyleft"
UNKNOWN = "Unknown"
PERMISSIVE = "Permissive"
# Descending attention required (AC #3).
TIER_ORDER = [STRONG_COPYLEFT, WEAK_COPYLEFT, UNKNOWN, PERMISSIVE]

_PERMISSIVE_SPDX = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "BSD-3-Clause-Clear",
    "ISC",
    "0BSD",
    "Unlicense",
    "Python-2.0",
    "PSF-2.0",
    "Zlib",
    "BSL-1.0",
    "CC0-1.0",
}

# Trove license classifiers → SPDX identifiers (controlled vocabulary from PyPI).
_CLASSIFIER_SPDX = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: BSD License": "BSD-3-Clause",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: The Unlicense (Unlicense)": "Unlicense",
    "License :: OSI Approved :: GNU General Public License v2 (GPLv2)": "GPL-2.0-only",
    "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)": "GPL-2.0-or-later",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)": "GPL-3.0-only",
    "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)": "GPL-3.0-or-later",
    "License :: OSI Approved :: GNU Affero General Public License v3": "AGPL-3.0-only",
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)": "AGPL-3.0-or-later",
    "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)": "LGPL-2.1-only",
    "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)": "LGPL-2.1-or-later",
    "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0-only",
    "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)": "LGPL-3.0-or-later",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}


def _extract_license(session: http.CachedLimiterSession, pkg: PackageSpec) -> str | None:
    """Return the package's SPDX-ish license id from PyPI metadata, or None if unknown."""
    try:
        response = session.get(f"{PYPI_JSON_URL}/{pkg.name}/{pkg.version}/json")
        response.raise_for_status()
        info = response.json().get("info", {})
    except (requests.RequestException, ValueError):
        return None  # best-effort → Unknown tier

    expression = (info.get("license_expression") or "").strip()
    if expression:
        return expression
    for classifier in info.get("classifiers", []):
        if classifier in _CLASSIFIER_SPDX:
            return _CLASSIFIER_SPDX[classifier]
    declared = (info.get("license") or "").strip()
    # A short declared value is likely an SPDX id; long free text is not classifiable.
    if declared and len(declared) <= 40 and "\n" not in declared:
        return declared
    return None


def _classify_license(spdx: str | None) -> str:
    """Place an SPDX id into one of the four tiers (AC #2/#4)."""
    if not spdx:
        return UNKNOWN
    upper = spdx.upper()
    if upper.startswith("AGPL"):
        return STRONG_COPYLEFT
    if upper.startswith("LGPL"):
        return WEAK_COPYLEFT
    if upper.startswith("GPL"):
        return STRONG_COPYLEFT
    if upper.startswith("MPL"):
        return WEAK_COPYLEFT
    if spdx in _PERMISSIVE_SPDX:
        return PERMISSIVE
    return UNKNOWN  # non-SPDX / unrecognized identifier


def classify(packages: list[PackageSpec], *, session: http.CachedLimiterSession | None = None) -> dict[str, Any]:
    """Classify each package's license into the four tiers and return the report dict (FR-5.2)."""
    session = session or http.pypi_session()

    buckets: dict[str, list[dict[str, str]]] = {tier: [] for tier in TIER_ORDER}
    for pkg in packages:
        spdx = _extract_license(session, pkg)
        buckets[_classify_license(spdx)].append(
            {"name": pkg.name, "version": pkg.version, "license": spdx or "UNKNOWN"}
        )

    return {
        "tiers": [{"tier": tier, "packages": buckets[tier]} for tier in TIER_ORDER],
        "summary": {tier: len(buckets[tier]) for tier in TIER_ORDER},
    }
