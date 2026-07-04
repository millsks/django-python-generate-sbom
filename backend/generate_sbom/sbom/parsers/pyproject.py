"""pyproject.toml resolver — tomllib parse then uv pip compile."""

from __future__ import annotations

import tomllib

from packaging.requirements import InvalidRequirement, Requirement

from ._types import PackageSpec, ResolutionError, tag_relationships
from ._uv import uv_pip_compile


def _declared_name(dep: str) -> str:
    """Best-effort direct-dependency name from a PEP 621 requirement string."""
    try:
        return Requirement(dep).name
    except InvalidRequirement:
        return dep


def resolve(content: bytes) -> list[PackageSpec]:
    """Extract dependencies (PEP 621 or Poetry) and resolve the transitive set."""
    try:
        data = tomllib.loads(content.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ResolutionError("pyproject.toml is not valid TOML.") from exc

    deps = list(data.get("project", {}).get("dependencies", []))
    if deps:
        declared = [_declared_name(str(dep)) for dep in deps]  # PEP 621: requirement strings
    else:
        poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        deps = [name for name in poetry if name.lower() != "python"]
        declared = list(deps)  # Poetry: keys are already names
    return tag_relationships(uv_pip_compile([str(dep) for dep in deps]), declared)
