"""conda environment.yml resolver — convert to a pixi manifest and solve with pixi.

The uploaded environment file is imported into a pixi workspace (pinned to linux-64 with
a cuda system requirement) and solved with ``pixi lock``; the resulting ``pixi.lock`` is
parsed by the shared pixi.lock parser (Story 8.19). Conda packages are tagged
``ecosystem=conda`` and the nested ``pip:`` extras ``pypi`` by that parser; the declared
dependencies (conda specs + ``pip:`` names) are tagged ``direct`` here.
"""

from __future__ import annotations

import re
from typing import Any

import yaml
from packaging.requirements import InvalidRequirement, Requirement

from . import pixi_lock
from ._pixi import pixi_lock_from_environment
from ._types import PackageSpec, ResolutionError, tag_relationships

# Split a conda match-spec on its first version/build/bracket/operator token → the name.
# Handles ``numpy=1.26``, ``numpy>=1.2`` and the bracket form ``python[version='>=3.12']``.
_CONDA_NAME_RE = re.compile(r"[\[=<>!~\s]")


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
    """Parse the environment file (safe) and resolve it via pixi."""
    try:
        data = yaml.safe_load(content.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise ResolutionError("environment.yml is not valid YAML.") from exc
    if not isinstance(data, dict):
        raise ResolutionError("environment.yml has an unexpected structure.")

    # pixi solves the environment (linux-64 + cuda) and writes a pixi.lock; the shared
    # parser reads the full set and tags conda/pypi ecosystems. Declared deps → direct.
    declared = _declared_names(data)
    resolved = pixi_lock.resolve(pixi_lock_from_environment(content, declared))
    return tag_relationships(resolved, declared)
