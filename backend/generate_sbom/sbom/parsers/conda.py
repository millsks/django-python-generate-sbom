"""conda environment.yml resolver — YAML parse then conda/mamba solve."""

from __future__ import annotations

import re
from typing import Any

import yaml
from packaging.requirements import InvalidRequirement, Requirement

from ._conda import conda_solve
from ._types import PackageSpec, ResolutionError, tag_relationships

# Split a conda match-spec on its first version/build/operator token → the name.
_CONDA_NAME_RE = re.compile(r"[=<>!~\s]")


def _declared_names(data: dict[str, Any]) -> list[str]:
    """Direct dependency names from ``dependencies:`` (conda specs + nested ``pip:``)."""
    names: list[str] = []
    for dep in data.get("dependencies", []) or []:
        if isinstance(dep, str):
            name = _CONDA_NAME_RE.split(dep, 1)[0].strip()
            if name:
                names.append(name)
        elif isinstance(dep, dict):  # e.g. {"pip": ["requests>=2", ...]}
            for pip_dep in dep.get("pip", []) or []:
                try:
                    names.append(Requirement(str(pip_dep)).name)
                except InvalidRequirement:
                    continue
    return names


def resolve(content: bytes) -> list[PackageSpec]:
    """Parse the environment file (safe) and resolve it via conda/mamba."""
    try:
        data = yaml.safe_load(content.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise ResolutionError("environment.yml is not valid YAML.") from exc
    if not isinstance(data, dict):
        raise ResolutionError("environment.yml has an unexpected structure.")
    return tag_relationships(conda_solve(data), _declared_names(data))
