"""Convert a conda ``environment.yml`` to a pixi workspace and solve it (Story 8.19).

Instead of shelling out to conda/mamba, an uploaded environment file is imported into a
pixi manifest (``pixi init --import``) and solved with pixi's own resolver
(``pixi lock`` — solve only, no install). The resolved ``pixi.lock`` is then parsed by
the existing pixi.lock parser.

The conversion is pinned to **linux-64** with a **cuda** system requirement so that
linux-only and CUDA-specific builds (e.g. ``libarrow[build='*cuda*']``,
``tensorflow[build='*cuda126*']``) can resolve regardless of the worker's own
architecture (the worker may be linux-aarch64, which has no CUDA builds). ``pixi lock``
solves for a declared platform without needing to run on it, so a fixed linux-64 target
is deterministic.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import tomllib
from collections.abc import Iterable
from pathlib import Path

from packaging.utils import canonicalize_name

from ._types import ResolutionError

# Conda environments are always resolved for this platform so linux-only / CUDA builds
# are available (verified: a bare linux-64 solve still needs __cuda for CUDA builds,
# which the cuda system-requirement below provides).
_PLATFORM = "linux-64"
_CUDA_VERSION = "12"
_TIMEOUT_SECONDS = 900

# Box-drawing block (U+2500-U+257F) plus the multiplication-sign / triangle / bullet
# glyphs pixi uses to format its solver error tree. Escapes keep the source ASCII.
_BOX_RE = re.compile("[─-╿×▶•]")  # noqa: RUF001  (box-drawing + tree glyphs pixi emits)


def pixi_lock_from_environment(content: bytes, declared_names: Iterable[str]) -> bytes:
    """Import ``content`` (an environment.yml) into a pixi workspace and return its lock.

    Raises ``ResolutionError`` (with the actual reason in the message) when a declared
    dependency cannot be represented in the pixi manifest, or when the environment cannot
    be solved.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        env_file = tmp_path / "environment.yml"
        env_file.write_bytes(content)
        workspace = tmp_path / "workspace"

        _run(["pixi", "init", str(workspace), "--platform", _PLATFORM, "--import", str(env_file)])

        # `pixi init --import` silently drops specs it cannot convert (e.g. private
        # packages, unusual version formats) — surface that instead of a silently
        # incomplete SBOM.
        manifest = workspace / "pixi.toml"
        _assert_all_declared_present(manifest, declared_names)

        # system-requirements has no CLI flag; append it so __cuda is provided to the solver.
        with manifest.open("a", encoding="utf-8") as handle:
            handle.write(f'\n[system-requirements]\ncuda = "{_CUDA_VERSION}"\n')

        _run(["pixi", "lock"], cwd=workspace)
        return (workspace / "pixi.lock").read_bytes()


def _assert_all_declared_present(manifest: Path, declared_names: Iterable[str]) -> None:
    """Fail if any declared dependency did not survive the pixi-manifest conversion."""
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    present = {
        canonicalize_name(str(key)) for table in ("dependencies", "pypi-dependencies") for key in data.get(table, {})
    }
    missing = sorted({name for name in declared_names if canonicalize_name(name) not in present})
    if missing:
        raise ResolutionError(
            "conda environment could not be resolved: these dependencies could not be "
            "converted to a pixi manifest (they may be unavailable on the configured "
            f"channels or use an unsupported version format): {', '.join(missing)}"
        )


def _clean_env() -> dict[str, str]:
    """Environment for the nested pixi calls, stripped of the outer workspace's pixi state.

    The worker runs under ``pixi run``, which exports ``PIXI_*`` / ``CONDA_*`` vars (e.g.
    ``PIXI_PROJECT_MANIFEST``) that would otherwise redirect the nested ``pixi`` at the
    app's own manifest. PATH and everything else are preserved.
    """
    return {k: v for k, v in os.environ.items() if not k.startswith(("PIXI_", "CONDA_"))}


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(
            cmd,
            cwd=cwd,
            env=_clean_env(),
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = _solver_problem(exc.stderr) or _solver_problem(exc.stdout) or "pixi could not solve the environment."
        raise ResolutionError(f"conda environment could not be resolved: {detail}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ResolutionError("conda environment resolution timed out.") from exc
    except FileNotFoundError as exc:  # pixi missing — should not happen in the worker
        raise ResolutionError("pixi is not available to resolve the conda environment.") from exc


def _solver_problem(output: str | None) -> str:
    """Pull the human-readable solver problem out of pixi's tree-formatted stderr."""
    if not output:
        return ""
    lines = [_BOX_RE.sub("", line).strip() for line in output.splitlines()]
    lines = [line for line in lines if line]
    for index, line in enumerate(lines):
        lowered = line.lower()
        if "cannot solve" in lowered or "no candidates" in lowered or "would require" in lowered:
            return " ".join(lines[index:])[:400]
    return ""
