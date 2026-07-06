"""Guard against frontend/backend manifest-format drift (Story 6.4, AC #4).

The History-page format dropdown derives its options from ``MANIFEST_FORMATS`` in
``frontend/src/api/manifestFormats.ts``. This test pins that constant to the backend
``ManifestUpload.Format`` enum — the single source of truth — so any rename/addition on
one side that isn't mirrored on the other fails CI instead of shipping a UI that offers
a value the backend rejects.
"""

from __future__ import annotations

import re
from pathlib import Path

from generate_sbom.manifests.models import ManifestUpload

# backend/tests/unit/<this file> -> repo root is three levels up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_FORMATS_TS = _REPO_ROOT / "frontend" / "src" / "api" / "manifestFormats.ts"


def _frontend_manifest_formats() -> list[str]:
    """Parse the ordered ``MANIFEST_FORMATS`` string array from the frontend TS constant."""
    source = _MANIFEST_FORMATS_TS.read_text(encoding="utf-8")
    match = re.search(r"export const MANIFEST_FORMATS\s*=\s*\[(.*?)\]", source, re.DOTALL)
    assert match is not None, "MANIFEST_FORMATS export not found in manifestFormats.ts"
    return re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))


def test_frontend_manifest_formats_match_backend_enum() -> None:
    """The frontend format codes equal the canonical ``ManifestUpload.Format`` values, in order."""
    assert _frontend_manifest_formats() == list(ManifestUpload.Format.values)
