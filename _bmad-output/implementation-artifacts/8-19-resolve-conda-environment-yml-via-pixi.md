# Story 8.19: Resolve conda environment.yml via pixi (replace the mamba solver)

Status: review

## Story

As a user, I want conda `environment.yml` uploads resolved through pixi, so they use the
project's native toolchain, reuse the pixi.lock parser, and drop the mamba/conda dependency —
while genuinely unsolvable environments fail with a clear reason.

## Acceptance Criteria

1. `conda.resolve()` converts the uploaded `environment.yml` to a pixi manifest
   (`pixi init --platform linux-64 --import`), solves it with `pixi lock` (solve only, isolated
   temp dir), and parses the resulting `pixi.lock` via the shared `pixi_lock.resolve` — conda
   ecosystem + direct/transitive tagging preserved.
2. The mamba/conda subprocess (`_conda.py`) is removed and `conda`+`mamba` are dropped from
   `pixi.toml` runtime dependencies (pixi is always present in the worker via `pixi run`).
3. A solvable `environment.yml` resolves to the expected package list (no `resolution_failed`).
4. A genuinely unsatisfiable env fails deliberately (still a `ResolutionError`) with the actual
   solver problem in the message (e.g. "nothing provides __cuda …"), not an opaque status.
5. The conversion is pinned to **linux-64** with a **cuda** system-requirement so linux-only /
   CUDA builds resolve regardless of the worker's architecture. Declared deps dropped during
   conversion are surfaced (not silently omitted from the SBOM).
6. `pixi run ci` green (backend coverage ≥90%); detection/format wiring for
   `environment.yml`/`.yaml` unchanged.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- New `sbom/parsers/_pixi.py`: `pixi_lock_from_environment` (init `--platform linux-64 --import`
  → append `[system-requirements] cuda="12"` → `pixi lock` → return lock bytes), with a
  completeness check (`_assert_all_declared_present`) and solver-error extraction
  (`_solver_problem`). Nested-pixi env vars (`PIXI_*`/`CONDA_*`) are stripped so the worker's
  own `pixi run` context doesn't hijack the solve.
- `conda.resolve()` now: parse env → pixi solve → `pixi_lock.resolve` → `tag_relationships`.
- `pixi_lock.resolve` fixed to read conda entries whose name/version live in the `conda:` URL.
- Removed `_conda.py` + `SolverUnavailableError`; dropped `conda`/`mamba` from `pixi.toml`.
- Real-solve verified: small env (37-41 pkgs) and `farm-environment.yaml` (547 conda pkgs, CUDA
  builds included). Parser modules at 100% unit coverage.

### File List

- backend/generate_sbom/sbom/parsers/_pixi.py (new)
- backend/generate_sbom/sbom/parsers/conda.py
- backend/generate_sbom/sbom/parsers/pixi_lock.py
- backend/generate_sbom/sbom/parsers/_types.py
- backend/generate_sbom/sbom/parsers/__init__.py
- backend/generate_sbom/sbom/parsers/_conda.py (removed)
- backend/tests/unit/test_parsers.py
- pixi.toml / pixi.lock
