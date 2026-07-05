# Story 8.21: Fix the PyPI → conda-forge equivalent (reverse) lookup

Status: review

## Story

As a user,
I want a PyPI package mapped to its correct conda-forge package,
so that the conda-forge latest / divergence lookup compares against the right package
(not a coincidentally same-named but unrelated one).

## Acceptance Criteria

1. `parselmouth.pypi_to_conda("build")` returns `python-build` (not the unrelated conda `build`).
2. The reverse map no longer prefers an identity (conda == pypi) tie-break; a curated override table resolves known ambiguous PyPI→conda cases, and normal 1:1 names are unaffected.
3. The Story 8.10 conda-forge latest / divergence lookup (`versions._conda_forge_latest`, which calls `pypi_to_conda`) uses the corrected mapping.
4. Tests cover the override, the identity/1:1 case, and override precedence; `pixi run ci` green; conda-forge data still via prefix.dev.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- `parselmouth._ensure_loaded`: removed the "prefer identity (conda == pypi)" tie-break when inverting the conda→PyPI map; inversion is now first-mapping-wins.
- Added `_PYPI_TO_CONDA_OVERRIDES` (canonical PyPI name → conda-forge name), seeded with `build → python-build`, applied with highest precedence in `pypi_to_conda` (override > inverted map > same-name fallback).
- `versions._conda_forge_latest` calls `parselmouth.pypi_to_conda` unchanged, so it now resolves the correct conda-forge package automatically; the prefix.dev GraphQL query path is untouched.
- Added 4 unit tests (build override, override-wins-over-stored, no-identity-preference, 1:1 unaffected); all 9 parselmouth tests pass.

### File List

- backend/generate_sbom/analysis/services/parselmouth.py
- backend/tests/unit/test_parselmouth.py
