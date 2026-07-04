"""Manifest parsers/resolvers (Story 3.3, F4).

Each format resolves manifest ``content`` to the full transitive package list.
Parsers are pure functions (AD-3): plain bytes in, list[PackageSpec] out.
"""

from __future__ import annotations

from collections.abc import Callable

from generate_sbom.manifests.models import ManifestUpload

from . import conda, pixi_lock, pixi_toml, pyproject, requirements
from ._types import (
    DIRECT,
    TRANSITIVE,
    UNKNOWN,
    PackageSpec,
    ResolutionError,
    SolverUnavailableError,
    tag_relationships,
)

_RESOLVERS: dict[str, Callable[[bytes], list[PackageSpec]]] = {
    ManifestUpload.Format.PIXI_LOCK: pixi_lock.resolve,
    ManifestUpload.Format.PIXI_TOML: pixi_toml.resolve,
    ManifestUpload.Format.PYPROJECT: pyproject.resolve,
    ManifestUpload.Format.CONDA: conda.resolve,
    ManifestUpload.Format.REQUIREMENTS: requirements.resolve,
}


def resolve_packages(manifest_format: str, content: bytes) -> list[PackageSpec]:
    """Resolve ``content`` (of the given format) to its full package list."""
    resolver = _RESOLVERS.get(manifest_format)
    if resolver is None:
        raise ResolutionError(f"No resolver for format {manifest_format!r}.")
    return resolver(content)


__all__ = [
    "DIRECT",
    "TRANSITIVE",
    "UNKNOWN",
    "PackageSpec",
    "ResolutionError",
    "SolverUnavailableError",
    "resolve_packages",
    "tag_relationships",
]
