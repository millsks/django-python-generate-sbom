"""pyproject.toml resolver — tomllib parse then uv pip compile."""

from __future__ import annotations

import tomllib

from ._types import PackageSpec, ResolutionError
from ._uv import uv_pip_compile


def resolve(content: bytes) -> list[PackageSpec]:
    """Extract dependencies (PEP 621 or Poetry) and resolve the transitive set."""
    try:
        data = tomllib.loads(content.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ResolutionError("pyproject.toml is not valid TOML.") from exc

    deps = list(data.get("project", {}).get("dependencies", []))
    if not deps:
        poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        deps = [name for name in poetry if name.lower() != "python"]
    return uv_pip_compile([str(dep) for dep in deps])
