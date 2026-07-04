"""conda/mamba solver subprocess wrapper for environment.yml (FR-4.3)."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import structlog
import yaml

from ._types import PackageSpec, ResolutionError, SolverUnavailableError

logger = structlog.get_logger()
_TIMEOUT_SECONDS = 600


def conda_solve(env: dict[str, Any]) -> list[PackageSpec]:
    """Resolve a conda environment to its full package set via conda/mamba."""
    solver = shutil.which("mamba") or shutil.which("conda")
    if solver is None:
        raise SolverUnavailableError(
            "Neither mamba nor conda is available to resolve the environment. "
            "conda/mamba is a required runtime dependency."
        )

    with tempfile.TemporaryDirectory() as tmp:
        env_file = Path(tmp) / "environment.yml"
        env_file.write_text(yaml.safe_dump(env), encoding="utf-8")
        try:
            result = subprocess.run(
                [solver, "env", "create", "--dry-run", "--json", "--file", str(env_file)],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SECONDS,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise ResolutionError(f"conda solve failed: {exc.stderr.strip()[:200]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ResolutionError("conda solve timed out.") from exc

    return parse_conda_json(result.stdout)


def parse_conda_json(output: str) -> list[PackageSpec]:
    """Extract the resolved package list from ``conda env create --dry-run --json``."""
    data = json.loads(output)
    linked = data.get("actions", {}).get("LINK", [])
    return [PackageSpec(name=pkg["name"], version=pkg["version"]) for pkg in linked]
