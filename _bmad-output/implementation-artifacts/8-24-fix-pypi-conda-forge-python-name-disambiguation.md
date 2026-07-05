# Story 8.24: Fix the PyPI to conda-forge Package Resolution (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user reading the version-currency report,
I want the conda-forge column to resolve to the conda-forge package that actually corresponds to the PyPI project,
so that version mismatches aren't reported against an unrelated same-named conda-forge package.

## Acceptance Criteria

1. **The bulk mapping is available from first boot.** Lookups no longer silently degrade to the same-name fallback because the weekly refresh hasn't run. The parselmouth `compressed_mapping.json` (or an equivalent snapshot) is loaded as the baseline on a fresh stack — not just the 3-entry seed. This alone fixes `xxhash → python-xxhash` and the ~19,700 single-match PyPI names.
2. **Ambiguous names resolve authoritatively.** For a PyPI name with **more than one** conda candidate in the bulk map (~297 of ~20,000, e.g. `build → {build, python-build}`), resolution uses parselmouth's **per-package, version-aware** data (`pypi-to-conda-v1/conda-forge/<name>.json`) — the authoritative "which conda package IS this PyPI project" answer — taking the conda name for the latest release (`build → python-build`). Only ambiguous names incur this extra (cached) lookup.
3. **Curated overrides stay highest precedence.** `_PYPI_TO_CONDA_OVERRIDES` is checked first — a fast path that also avoids the per-package call for known cases (e.g. `build`).
4. **No regression + graceful degradation.** Single-match names are unchanged (`torch → pytorch`, `requests → requests`); if the per-package lookup fails (network/404), fall back deterministically (curated override → the bulk map's first candidate → same name) and never raise.
5. **Tested; CI green.** Unit tests (no live network) cover: `xxhash → python-xxhash` from a loaded snapshot; an ambiguous name resolved via a **mocked** per-package response (`build → python-build`); a single-match passthrough; override precedence; and per-package-lookup failure falling back cleanly. `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Confirm parselmouth's per-package endpoint + shape (AC: #2)**
  - [ ] The parselmouth web app (`prefix-dev.github.io/parselmouth?q=build&dir=pypi`) loads `pypi-to-conda-v1/conda-forge/<name>.json` (visible as a link), but that path 404s under `main/files/` — determine the real URL (inspect the web app's network requests / parselmouth repo/README) and the JSON shape (a PyPI-version → conda-name history). Record the base URL as a setting (like `PARSELMOUTH_MAPPING_URL`).
- [ ] **Task 2 — Load the bulk map from first boot (AC: #1)**
  - [ ] Ensure `compressed_mapping.json` is present without waiting for the weekly beat: bundle a committed snapshot loaded as the baseline in `_ensure_loaded` (superset of `_SEED_CONDA_TO_PYPI`), and/or run `refresh_parselmouth_mapping` eagerly on first use. Keep the weekly refresh to update it. Goal: same-name fallback becomes the rare exception, not the fresh-stack default.
- [ ] **Task 3 — Detect ambiguity + authoritative resolve (AC: #2, #3, #4)**
  - [ ] In `_ensure_loaded` (`parselmouth.py:64-77`), record PyPI names claimed by >1 non-null conda candidate (an `_ambiguous: set[str]`). Skip `pypi_name is None` as today (that's why `xxhash → None` is correctly dropped, leaving only `python-xxhash`).
  - [ ] In `pypi_to_conda` (`parselmouth.py:80-90`): override → if the name is ambiguous, resolve via the per-package endpoint (Task 1), latest release's conda name, **cached** (reuse a `CachedLimiterSession` per `http.py`) → else the inverted bulk map → same name. On per-package failure, fall back per AC #4 (never raise).
- [ ] **Task 4 — Tests (AC: #5)**
  - [ ] Fixture-load a snapshot containing `python-xxhash→xxhash`, `xxhash→None`, `build→build`, `python-build→build`, `pytorch→torch`; assert `xxhash→python-xxhash`, `torch→pytorch`, `requests→requests`. Mock the per-package endpoint for `build`→`python-build`; assert an override still wins; assert a failed per-package call degrades cleanly. Use `_invalidate()` between cases; no live network.

## Dev Notes

### Verified data (from the live `compressed_mapping.json`, 33,415 entries)

- **`xxhash` is unambiguous:** `python-xxhash → xxhash`, `xxhash → None`, `types-xxhash → types-xxhash`. The loader skips the `None`, so a **loaded** map already yields `xxhash → python-xxhash`. The user's wrong result means the map **wasn't loaded** (weekly refresh + empty MinIO → seed only → `pypi_to_conda` same-name fallback at `parselmouth.py:90`). → Task 2 is the fix for this class.
- **`build` is genuinely ambiguous:** both `build → build` and `python-build → build`. The name→name map can't disambiguate; parselmouth's per-package `build.json` history shows every PyPI release → `python-build`. → Task 3 (authoritative per-package lookup) is the fix for this class.
- **Scale:** 297 of ~20,000 PyPI targets (~1.5%) have >1 conda candidate, with no consistent name shape (`build`/`python-build`, `aesara`/`aesara-base`, `dvc`/`_dvc`/`dvc-base`, `apache-airflow`/`airflow`) — confirming a name-shape heuristic is NOT viable; the per-package data is the only reliable disambiguator.

### Design (decided with the user)

Bulk map for the unambiguous 98.5% (cheap, offline); parselmouth's authoritative per-package `pypi-to-conda-v1` data for the ambiguous ~1.5% (one cached call each); curated overrides as the fast-path/authority. This is the "better lookup" — not listing multiple candidates in the report, and not a `python-` string guess.

### Consumers / caution

- `versions._conda_forge_latest` (`versions.py:166-175`) uses `pypi_to_conda` then queries prefix.dev — a correct conda name → correct "conda-forge Latest" and `latest_mismatch`. Backend-only; report + Excel export benefit transitively.
- Per-package lookups must be cached + rate-limited (mirror `http.py`'s `CachedLimiterSession`) and only fire for ambiguous names. Tests never hit the network.

### References

- User evidence: parselmouth `?q=xxhash&dir=pypi` → `python-xxhash`; `?q=build&dir=pypi` → 2 candidates (`build`, `python-build`), history → `python-build`.
- `backend/generate_sbom/analysis/services/parselmouth.py:37,57-77,80-90`; `versions.py:166-175`; `http.py` (CachedLimiterSession)
- `backend/config/settings/base.py:173` (`PARSELMOUTH_MAPPING_URL`), `config/celery_app.py:24` (weekly refresh), `tasks/maintenance.py:19`
- Related: `8-21-fix-pypi-to-conda-forge-reverse-lookup.md`, `8-10-conda-forge-latest-and-divergence.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
