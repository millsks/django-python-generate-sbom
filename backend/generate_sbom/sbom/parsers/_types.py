"""Shared types and errors for manifest parsing/resolution (Story 3.3)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from packaging.utils import canonicalize_name

# Dependency relationship values (Story 8.3, AD-14). ``unknown`` is the default and
# the fallback where a format can't identify the declared set (e.g. pixi.lock).
DIRECT = "direct"
TRANSITIVE = "transitive"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class PackageSpec:
    """A resolved package: name + pinned version (+ optional extras/markers)."""

    name: str
    version: str
    extras: tuple[str, ...] = ()
    markers: str = ""
    relationship: str = UNKNOWN  # direct | transitive | unknown (Story 8.3)


def tag_relationships(specs: list[PackageSpec], declared_names: Iterable[str]) -> list[PackageSpec]:
    """Tag each spec ``direct`` if its canonical name is in the declared set, else ``transitive``.

    Declared-set intersection by PEP 503 name (AD-14, Story 8.2 spike): a resolved
    package the manifest declared is direct; everything else is transitive. A package
    both declared and pulled transitively resolves to direct (declared wins).
    """
    declared = {canonicalize_name(name) for name in declared_names}
    return [
        replace(spec, relationship=DIRECT if canonicalize_name(spec.name) in declared else TRANSITIVE) for spec in specs
    ]


class ResolutionError(Exception):
    """A manifest could not be resolved (parse or resolver failure)."""


class SolverUnavailableError(ResolutionError):
    """The conda/mamba solver binary is not available (a required runtime dep)."""
