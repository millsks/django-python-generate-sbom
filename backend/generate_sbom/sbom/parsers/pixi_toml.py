"""pixi.toml resolver — TOML parse; dependency names → uv pip compile (no lock)."""

from __future__ import annotations

import tomllib

from ._types import PackageSpec, ResolutionError, tag_relationships
from ._uv import uv_pip_compile


def resolve(content: bytes) -> list[PackageSpec]:
    """Extract dependency names and resolve the transitive set via uv."""
    try:
        data = tomllib.loads(content.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ResolutionError("pixi.toml is not valid TOML.") from exc

    names: list[str] = []  # declared (direct) dependency names
    for section in ("dependencies", "pypi-dependencies"):
        for name in data.get(section, {}):
            if name.lower() != "python":
                names.append(str(name))
    return tag_relationships(uv_pip_compile(names), names)
