"""requirements.txt resolver — parse then uv pip compile for the transitive tree."""

from __future__ import annotations

from packaging.requirements import InvalidRequirement, Requirement

from ._types import PackageSpec, ResolutionError
from ._uv import uv_pip_compile


def resolve(content: bytes) -> list[PackageSpec]:
    """Parse requirement lines (safe) and resolve the full transitive set."""
    lines: list[str] = []
    for raw in content.decode("utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        try:
            Requirement(line)
        except InvalidRequirement as exc:
            raise ResolutionError(f"Invalid requirement: {line!r}") from exc
        lines.append(line)
    return uv_pip_compile(lines)
