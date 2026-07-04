"""pixi.toml resolver — TOML parse; dependency names → uv pip compile (no lock)."""

from __future__ import annotations

import tomllib

from ._types import PackageSpec, ResolutionError, tag_ecosystems, tag_relationships
from ._uv import uv_pip_compile


def _names(data: dict[str, object], section: str) -> list[str]:
    table = data.get(section)
    if not isinstance(table, dict):
        return []
    return [str(name) for name in table if str(name).lower() != "python"]


def resolve(content: bytes) -> list[PackageSpec]:
    """Extract dependency names and resolve the transitive set via uv."""
    try:
        data = tomllib.loads(content.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ResolutionError("pixi.toml is not valid TOML.") from exc

    conda_names = _names(data, "dependencies")  # conda deps (Story 8.8)
    declared = conda_names + _names(data, "pypi-dependencies")
    # Resolution flattens via uv (PyPI): tag the declared conda names conda, the rest pypi.
    resolved = tag_relationships(uv_pip_compile(declared), declared)
    return tag_ecosystems(resolved, conda_names)
