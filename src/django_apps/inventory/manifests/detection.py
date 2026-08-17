"""Manifest format detection and safe-parse validation (FR-3.3, FR-3.4).

Detection is by filename (with an optional explicit override); content is then
validated with safe loaders only — never eval/exec/shell (NFR-3.1).
"""

from __future__ import annotations

import re
import tomllib

import yaml

from .models import ManifestUpload

_Format = ManifestUpload.Format
SUPPORTED = "requirements.txt, pyproject.toml, pixi.lock, pixi.toml, environment.yml"

# Each manifest type is recognized by its core token plus its extension, with an
# optional prefix and/or suffix around the token — e.g. requirements.txt,
# dev-requirements.txt, requirements-test.txt; backend-pyproject.toml,
# pyproject-old.toml; pixi-prod.lock; dev-environment.yaml. Matched with re.search
# so a prefix before the token is allowed; ``[\w.-]*`` allows a suffix after it.
# The core tokens are distinct, so a filename matches at most one type; order only
# resolves pathological names carrying two tokens.
_FORMAT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"requirements[\w.-]*\.txt$"), _Format.REQUIREMENTS),
    (re.compile(r"pyproject[\w.-]*\.toml$"), _Format.PYPROJECT),
    (re.compile(r"pixi[\w.-]*\.toml$"), _Format.PIXI_TOML),
    (re.compile(r"pixi[\w.-]*\.lock$"), _Format.PIXI_LOCK),
    (re.compile(r"environment[\w.-]*\.ya?ml$"), _Format.CONDA),
)


class UnsupportedFormatError(Exception):
    """Raised when a manifest's format cannot be determined or is unsupported."""


class ManifestParseError(Exception):
    """Raised when a manifest's content fails to parse with a safe loader."""


def detect_format(filename: str) -> str:
    """Return the manifest format for ``filename`` or raise UnsupportedFormatError."""
    name = filename.lower()
    for pattern, fmt in _FORMAT_PATTERNS:
        if pattern.search(name):
            return fmt
    raise UnsupportedFormatError(f"Unsupported manifest format. Supported: {SUPPORTED}")


def validate_parseable(manifest_format: str, content: bytes) -> None:
    """Safe-parse ``content`` for its format; raise ManifestParseError on failure."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestParseError("Manifest is not valid UTF-8 text.") from exc

    try:
        if manifest_format in {_Format.PYPROJECT, _Format.PIXI_TOML}:
            tomllib.loads(text)
        elif manifest_format in {_Format.PIXI_LOCK, _Format.CONDA}:
            yaml.safe_load(text)
        # requirements.txt has no structured grammar to validate beyond decoding.
    except (tomllib.TOMLDecodeError, yaml.YAMLError) as exc:
        raise ManifestParseError("Manifest content could not be parsed.") from exc
