"""Shared types and errors for manifest parsing/resolution (Story 3.3)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackageSpec:
    """A resolved package: name + pinned version (+ optional extras/markers)."""

    name: str
    version: str
    extras: tuple[str, ...] = ()
    markers: str = ""


class ResolutionError(Exception):
    """A manifest could not be resolved (parse or resolver failure)."""


class SolverUnavailableError(ResolutionError):
    """The conda/mamba solver binary is not available (a required runtime dep)."""
