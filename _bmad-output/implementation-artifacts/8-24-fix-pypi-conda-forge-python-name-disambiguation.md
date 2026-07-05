# Story 8.24: Fix the PyPI to conda-forge Package Resolution (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user reading the version-currency report,
I want the conda-forge column to resolve to the package that actually reports the PyPI project's metadata,
so that version mismatches aren't reported against an unrelated same-named conda-forge package.

## Acceptance Criteria

1. **Authoritative resolution via parselmouth's data.** `pypi_to_conda(name)` returns the conda-forge package that **reports PyPI metadata for** that PyPI name — parselmouth's own rule. For `xxhash` that is **`python-xxhash`** (the bare conda `xxhash` is an unrelated C library that reports no PyPI metadata for `xxhash`). Reference: `https://prefix-dev.github.io/parselmouth/?q=xxhash&dir=pypi`.
2. **Root cause identified, not guessed.** The fix is chosen from the actual `compressed_mapping.json` data (see Task 1), not a name-shape assumption.
3. **No regression.** Existing renames still resolve (`torch → pytorch`), and PyPI names with a single conda match are unchanged (`requests → requests`).
4. **Reliable availability.** A lookup never silently degrades to the same-name fallback because the weekly mapping refresh hasn't run — the mapping is available from first boot (see Task 2).
5. **Curated overrides stay authoritative** for any residual exception.
6. **Tested; CI green.** Unit tests cover `xxhash → python-xxhash`, an existing rename, a single-match passthrough, and override precedence. `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Inspect the real mapping data first (AC: #2)**
  - [ ] Fetch `compressed_mapping.json` (`PARSELMOUTH_MAPPING_URL`, `backend/config/settings/base.py:173-175`) and inspect the entries around `xxhash`. Determine which is true:
    - **(a)** only `"python-xxhash": "xxhash"` exists → our lookup returns `xxhash` because the mapping **isn't loaded** in the running env (weekly beat + MinIO empty) and `pypi_to_conda` hits the same-name fallback (`parselmouth.py:90`). Root cause = availability, fix via Task 2.
    - **(b)** both `"xxhash": "xxhash"` (or similar) and `"python-xxhash": "xxhash"` exist → the inverted map is genuinely ambiguous and "first-wins" (`parselmouth.py:75`) picks the wrong one. Root cause = tiebreak, fix via Task 3.
  - [ ] Record the finding in the PR; it decides whether Task 2, Task 3, or both are needed.
- [ ] **Task 2 — Make the authoritative mapping reliably available (AC: #4) [if 1a]**
  - [ ] Ensure lookups use the real parselmouth mapping without waiting a week: e.g. **bundle a snapshot** of `compressed_mapping.json` in the repo and load it as the baseline (seed superset) in `_ensure_loaded`, and/or run `refresh_parselmouth_mapping` on startup. Goal: a same-name fallback is the rare exception, not the default in a fresh stack.
- [ ] **Task 3 — Deterministic tiebreak honoring parselmouth's model (AC: #1, #3) [if 1b]**
  - [ ] When multiple conda names map to one PyPI name during inversion (`_ensure_loaded`, `parselmouth.py:64-77`), choose the one that reports that PyPI project's metadata — matching parselmouth's UI. In the compressed map that means preferring the conda entry whose canonical name is `python-<pypi_name>` over an unrelated same-named entry. Keep this data-driven (only applies when both candidates actually appear in the mapping), not a blanket string rewrite; do not `python-`-prefix names that have no such conda variant.
- [ ] **Task 4 — Overrides remain the final authority (AC: #5)**
  - [ ] Keep `_PYPI_TO_CONDA_OVERRIDES` (`parselmouth.py:37`, checked first in `pypi_to_conda`) for any exception the data-driven fix can't express.
- [ ] **Task 5 — Tests (AC: #6)**
  - [ ] `backend/tests/unit/` (mirror existing parselmouth tests): with a mapping fixture reflecting the real data found in Task 1, `pypi_to_conda("xxhash") == "python-xxhash"`; `torch → pytorch` and `requests → requests` unchanged; an `_PYPI_TO_CONDA_OVERRIDES` entry still wins. If Task 2 applies, test that the bundled snapshot loads so resolution works before any refresh.

## Dev Notes

### The correct mental model (from the user)

Parselmouth answers "PyPI X → conda-forge" as **"the conda-forge package(s) that report PyPI metadata for X."** For PyPI `xxhash` that is exactly `python-xxhash`; the bare conda `xxhash` is a different project (a C library) that shares the name. So the fix must resolve to what parselmouth's data says reports the metadata — never a coincidental same-name. My earlier framing ("prefer `python-<name>` by string") was only a proxy; the real signal is the reports-metadata relationship in `compressed_mapping.json`.

### How our code resolves today (verified)

- `versions._conda_forge_latest` (`versions.py:166-175`) calls `parselmouth.pypi_to_conda(pypi_name)` then queries prefix.dev for the conda-forge latest — so a wrong conda name yields a wrong "conda-forge Latest" / false `latest_mismatch`.
- `parselmouth.pypi_to_conda` (`parselmouth.py:80-90`): curated override → inverted parselmouth map (`_ensure_loaded`, first-wins) → **same name**.
- `PARSELMOUTH_MAPPING_URL` default = `https://raw.githubusercontent.com/prefix-dev/parselmouth/main/files/compressed_mapping.json`; refreshed **weekly** by the `refresh-parselmouth-mapping` beat task (`config/celery_app.py:24`) into `default_storage`. **No bundled copy**, so before the first refresh only `_SEED_CONDA_TO_PYPI` (pytorch/tensorflow/faiss) is present and everything else same-name-falls-back — a strong candidate for why `xxhash` (and possibly others) resolve wrong in practice.

### Caution / scope

- Backend only: `parselmouth.py` (+ possibly a bundled `compressed_mapping.json` asset and its loader) and tests. No API/frontend change — the version-currency report + Excel export benefit transitively.
- Tests must not hit the network: use a fixture mapping / the bundled snapshot and `_invalidate()` between cases.

### References

- User evidence: parselmouth web app, `?q=xxhash&dir=pypi` → conda `python-xxhash` reports PyPI metadata for `xxhash`.
- `backend/generate_sbom/analysis/services/parselmouth.py:37,57-77,80-90`; `versions.py:166-175`
- `backend/config/settings/base.py:173` (URL), `backend/config/celery_app.py:24` (weekly refresh), `backend/generate_sbom/tasks/maintenance.py:19` (refresh task)
- Related: `8-21-fix-pypi-to-conda-forge-reverse-lookup.md`, `8-10-conda-forge-latest-and-divergence.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
