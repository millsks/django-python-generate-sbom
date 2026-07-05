"""pixi.lock resolver — YAML (NOT tomllib); full resolved set read directly."""

from __future__ import annotations

from typing import Any

import yaml

from ._types import CONDA, PYPI, PackageSpec, ResolutionError


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
        if not isinstance(pkg, dict):
            continue
        # Each entry is discriminated by a ``conda:`` or ``pypi:`` source key (Story 8.8).
        # pypi entries carry explicit name/version; modern (v7) conda entries do not —
        # their name/version live in the ``conda:`` URL filename (``<name>-<version>-<build>``).
        if "conda" in pkg:
            name_version = _conda_name_version(pkg)
            if name_version is not None:
                specs.append(PackageSpec(name=name_version[0], version=name_version[1], ecosystem=CONDA))
        else:
            name, version = pkg.get("name"), pkg.get("version")
            if name and version is not None:
                specs.append(PackageSpec(name=str(name), version=str(version), ecosystem=PYPI))
    return specs


def _conda_name_version(pkg: dict[str, Any]) -> tuple[str, str] | None:
    """Name + version for a conda lock entry: explicit fields if present, else the URL."""
    name, version = pkg.get("name"), pkg.get("version")
    if name and version is not None:
        return str(name), str(version)

    url = pkg.get("conda")
    if not isinstance(url, str):
        return None
    filename = url.rsplit("/", 1)[-1]
    for suffix in (".conda", ".tar.bz2"):
        if filename.endswith(suffix):
            filename = filename[: -len(suffix)]
            break
    # conda package filename: ``<name>-<version>-<build>`` (name may contain hyphens).
    parts = filename.rsplit("-", 2)
    if len(parts) != 3:
        return None
    return parts[0], parts[1]
