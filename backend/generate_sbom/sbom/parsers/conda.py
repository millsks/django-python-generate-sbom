"""conda environment.yml resolver — YAML parse then conda/mamba solve."""

from __future__ import annotations

import yaml

from ._conda import conda_solve
from ._types import PackageSpec, ResolutionError


def resolve(content: bytes) -> list[PackageSpec]:
    """Parse the environment file (safe) and resolve it via conda/mamba."""
    try:
        data = yaml.safe_load(content.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise ResolutionError("environment.yml is not valid YAML.") from exc
    if not isinstance(data, dict):
        raise ResolutionError("environment.yml has an unexpected structure.")
    return conda_solve(data)
