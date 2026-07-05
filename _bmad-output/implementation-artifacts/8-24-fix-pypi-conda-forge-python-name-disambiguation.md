# Story 8.24: Fix PyPI → conda-forge python-<name> Disambiguation (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user reading the version-currency report,
I want the conda-forge column to resolve to the correct package when a PyPI name collides with a non-Python conda-forge package,
so that version mismatches aren't reported against the wrong conda-forge package.

## Acceptance Criteria

1. **`python-<name>` wins on collision.** When conda-forge has both a same-named package and a `python-<pypi_name>` variant for a PyPI name, `pypi_to_conda(name)` returns the `python-<name>` variant. `xxhash → python-xxhash` and `build → python-build` both resolve correctly.
2. **No regression for non-collision names.** A PyPI package with no `python-<name>` conda variant is unchanged: `requests → requests`, `torch → pytorch` (existing rename), same-name fallback still works.
3. **Curated overrides stay authoritative.** `_PYPI_TO_CONDA_OVERRIDES` remains highest precedence for exceptions the heuristic can't cover.
4. **Tested; CI green.** Unit tests cover `xxhash`, `build`, an unchanged non-python case, and override precedence. `pixi run ci` is green.

## Tasks / Subtasks

- [ ] **Task 1 — Prefer `python-<name>` during inversion (AC: #1, #2)**
  - [ ] In `backend/generate_sbom/analysis/services/parselmouth.py` `_ensure_loaded()` (the inversion loop, ~lines 64-77), change "first mapping wins" so a conda candidate whose canonical name equals `python-<pypi_key>` **overrides** a previously-stored non-python candidate for that `pypi_key`. Keep first-wins among equally-ranked candidates. Concretely: when iterating `conda_name → pypi_name`, set `pypi_to_conda[pypi_key] = conda_name` if the slot is empty **or** `conda_key == f"python-{pypi_key}"` (the python-binding convention) and the current slot isn't already that.
  - [ ] Do not prefer a bare identity match over a real rename (the existing comment about conda `build` vs PyPI `build` must still hold).
- [ ] **Task 2 — Overrides remain authoritative (AC: #3)**
  - [ ] Leave `_PYPI_TO_CONDA_OVERRIDES` checked first in `pypi_to_conda` (`parselmouth.py:88-90`). The `build → python-build` entry becomes redundant with the heuristic but is harmless; keep it as a documented anchor (or note it's now covered — dev's discretion). Add an override only if a real case can't be expressed by the heuristic.
- [ ] **Task 3 — Tests (AC: #4)**
  - [ ] `backend/tests/unit/` (mirror the existing parselmouth tests): with a stored/seed mapping containing both `xxhash → xxhash` and `python-xxhash → xxhash`, `pypi_to_conda("xxhash") == "python-xxhash"`. Same for `build`. Assert `requests → requests` and `torch → pytorch` unchanged. Assert an entry in `_PYPI_TO_CONDA_OVERRIDES` still wins over the heuristic.

## Dev Notes

### Root cause (verified)

`pypi_to_conda` (`parselmouth.py:80-90`): override map → inverted parselmouth map → same name. The inversion in `_ensure_loaded` (`:70-76`) uses `if pypi_key not in pypi_to_conda` (first-wins), so for a PyPI name mapped-to by multiple conda names (e.g. conda `xxhash` and `python-xxhash` both point at PyPI `xxhash`), whichever appears first in the mapping JSON wins — often the wrong (C-library) one. `canonicalize_name` (packaging) normalizes both sides, so `python-<pypi_key>` compares cleanly.

### Why a heuristic, not just another override

`_PYPI_TO_CONDA_OVERRIDES` only has `build → python-build` today; every collision currently needs a hand-curated entry. Preferring the `python-<pypi_name>` conda candidate during inversion fixes the entire class (xxhash, build, and future ones) automatically, matching conda-forge's naming convention where the Python binding of a clashing name is `python-<name>`. Overrides stay as the escape hatch for the rare exception.

### Scope / caution

- Backend only, `parselmouth.py` + tests. No API/schema/frontend change — the version-currency report and its Excel export consume `pypi_to_conda` transitively, so they benefit automatically.
- Do not fetch the network for the mapping in tests — use a seeded/stored mapping fixture (the module loads `_SEED_CONDA_TO_PYPI` + the stored file; tests can inject via the seed or a `default_storage` fixture and `_invalidate()` between cases).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.24: Fix PyPI → conda-forge python-<name> Disambiguation (Bugfix)]
- `backend/generate_sbom/analysis/services/parselmouth.py:37` (`_PYPI_TO_CONDA_OVERRIDES`), `:57-77` (`_ensure_loaded` inversion), `:80-90` (`pypi_to_conda`)
- `backend/generate_sbom/analysis/services/versions.py:166-175` (`_conda_forge_latest` consumes `pypi_to_conda`)
- Related: `8-21-fix-pypi-to-conda-forge-reverse-lookup.md`, `8-10-conda-forge-latest-and-divergence.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
