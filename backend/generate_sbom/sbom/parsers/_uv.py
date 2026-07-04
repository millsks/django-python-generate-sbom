"""`uv pip compile` subprocess wrapper for transitive resolution (FR-4.3).

Receives file PATHS only — never file content as shell args (security design).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import structlog
from packaging.requirements import Requirement

from ._types import PackageSpec, ResolutionError

logger = structlog.get_logger()
_TIMEOUT_SECONDS = 300


def uv_pip_compile(requirement_lines: list[str]) -> list[PackageSpec]:
    """Resolve direct requirements to a full pinned set via ``uv pip compile``."""
    uv_bin = shutil.which("uv")
    if uv_bin is None:
        raise ResolutionError("uv is not available to resolve dependencies.")
    if not requirement_lines:
        return []

    with tempfile.TemporaryDirectory() as tmp:
        infile = Path(tmp) / "requirements.in"
        infile.write_text("\n".join(requirement_lines) + "\n", encoding="utf-8")
        try:
            result = subprocess.run(
                [uv_bin, "pip", "compile", str(infile), "--no-header", "--quiet"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SECONDS,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise ResolutionError(f"uv pip compile failed: {exc.stderr.strip()[:200]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ResolutionError("uv pip compile timed out.") from exc

    return parse_compiled(result.stdout)


def parse_compiled(output: str) -> list[PackageSpec]:
    """Parse ``uv pip compile`` output (pinned ``name==version`` lines)."""
    specs: list[PackageSpec] = []
    for raw in output.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-") or "==" not in line:
            continue
        req = Requirement(line)
        version = next((s.version for s in req.specifier if s.operator == "=="), "")
        specs.append(
            PackageSpec(
                name=req.name,
                version=version,
                extras=tuple(sorted(req.extras)),
                markers=str(req.marker) if req.marker else "",
            )
        )
    return specs
