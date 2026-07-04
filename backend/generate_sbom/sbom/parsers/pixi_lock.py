"""pixi.lock resolver — YAML (NOT tomllib); full resolved set read directly."""

from __future__ import annotations

import yaml

from ._types import PackageSpec, ResolutionError


def resolve(content: bytes) -> list[PackageSpec]:
    """Read the fully-resolved package set from a pixi.lock (no external resolver)."""
    try:
        data = yaml.safe_load(content.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise ResolutionError("pixi.lock is not valid YAML.") from exc
    if not isinstance(data, dict):
        raise ResolutionError("pixi.lock has an unexpected structure.")

    specs: list[PackageSpec] = []
    for pkg in data.get("packages", []):
        if isinstance(pkg, dict) and pkg.get("name") and pkg.get("version") is not None:
            specs.append(PackageSpec(name=str(pkg["name"]), version=str(pkg["version"])))
    return specs
