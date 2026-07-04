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

_REQUIREMENTS_RE = re.compile(r"^requirements.*\.txt$")


class UnsupportedFormatError(Exception):
    """Raised when a manifest's format cannot be determined or is unsupported."""


class ManifestParseError(Exception):
    """Raised when a manifest's content fails to parse with a safe loader."""


def detect_format(filename: str) -> str:
    """Return the manifest format for ``filename`` or raise UnsupportedFormatError."""
    name = filename.lower()
    if name == "pixi.lock":
        return _Format.PIXI_LOCK
    if name == "pixi.toml":
        return _Format.PIXI_TOML
    if name == "pyproject.toml":
        return _Format.PYPROJECT
    if name in {"environment.yml", "environment.yaml"}:
        return _Format.CONDA
    if _REQUIREMENTS_RE.match(name):
        return _Format.REQUIREMENTS
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
