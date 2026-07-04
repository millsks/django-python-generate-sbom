# Story 8.1: Broaden LTS Coverage via endoflife.date

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want the version-currency report's LTS data to cover far more than Django and Python,
so that the "on LTS / LTS target" signal is useful across my real dependency set.

## Acceptance Criteria

1. Given a resolved package whose project is tracked on endoflife.date, when the version-currency phase runs, then its LTS series is derived from the endoflife.date API (the latest release cycle whose `lts` field is truthy) and the entry's `lts` / `on_lts` reflect that.
2. Given the endoflife.date lookups, when they are performed, then they go through the shared cached, rate-limited, retrying HTTP session (the same pattern as OSV/PyPI/NVD) so repeated runs and packages shared across jobs do not re-hit the API.
3. Given a package with no endoflife.date entry, or the API is unreachable/errors, when LTS is determined, then it falls back to the static `SBOM_LTS_REGISTRY` + built-in defaults; if neither has it, the package is reported untracked (`lts: null`, `on_lts: null`) — never a fabricated LTS.
4. Given a package name that differs from its endoflife.date product slug, when the lookup is attempted, then a name→product mapping resolves the common cases; unmapped names fall through to untracked with no crash and no wrong match.
5. Given an explicit registry entry (built-in default or `SBOM_LTS_REGISTRY`) names a series for a package, when both it and an API-derived value exist, then the explicit registry entry wins (operator override is authoritative).
6. Given the endoflife.date `lts` field can be a boolean or a date string, when the latest LTS cycle is selected, then both encodings are handled and the cycle identifier (e.g. `"4.2"`) is used as the LTS series.

## Tasks / Subtasks

- [ ] Task 1 — endoflife.date HTTP session (AC: #2)
  - [ ] Add an `eol_session()` singleton in `analysis/services/http.py` mirroring `pypi_session`/`osv_session` (CachedLimiterSession + `external_retry`)
  - [ ] Base URL `https://endoflife.date/api`; per-product path `/{product}.json`
- [ ] Task 2 — LTS lookup service (AC: #1, #3, #4, #6)
  - [ ] In `analysis/services/versions.py`, add `_eol_lts_series(session, name)` that fetches `/{product}.json`, picks the latest cycle whose `lts` is truthy (bool `True` or a date string), and returns its `cycle` string, else `None`
  - [ ] Handle `requests.RequestException` / `ValueError` (bad JSON) → `None` (fall back), never raise out of the phase
  - [ ] Add a name→product slug map (`_EOL_PRODUCTS`) for common cases where the PyPI name ≠ endoflife.date slug; normalize via the existing `_normalize`
- [ ] Task 3 — Resolution order (AC: #1, #3, #5)
  - [ ] In `classify`, resolve LTS as: explicit `registry.get(name)` first (override wins); else endoflife.date-derived series; else `None`
  - [ ] Keep `on_lts` computed by the existing `_is_on_lts(installed, lts)` against whichever series was chosen
- [ ] Task 4 — Settings/session wiring (AC: #2)
  - [ ] Reuse the requests-cache backend already configured (`REQUESTS_CACHE_BACKEND`); no new runtime dependency
- [ ] Task 5 — Tests
  - [ ] Unit (responses): a tracked product (e.g. `django`) with mixed cycles picks the latest LTS cycle; boolean-`lts` and date-`lts` both handled
  - [ ] Unit: untracked product → falls back to registry, then untracked; API error → fallback (no raise)
  - [ ] Unit: explicit registry entry overrides the API-derived series
  - [ ] Unit: name→product mapping resolves a renamed case; an unmapped name falls through to untracked
  - [ ] `pixi run ci` exits 0 with ≥90% coverage on the new code

## Dev Notes

### endoflife.date API shape

`GET https://endoflife.date/api/{product}.json` returns an array of release cycles, most-recent first, each like:

```json
{ "cycle": "4.2", "releaseDate": "2023-04-03", "eol": "2026-04-01", "latest": "4.2.11", "lts": "2023-04-03", "support": "2024-12-04" }
```

`lts` is `false` when the cycle is not an LTS, `true` when it is, or a **date string** when LTS began on that date. Select the latest cycle where `lts` is truthy and use its `cycle` (e.g. `"4.2"`) as the LTS series — the same shape the version service already compares against with `Version(lts).release[:2]`. [Source: https://endoflife.date/docs/api]

### Existing LTS mechanics (Story 4.5 + PR #42)

`versions.py` already carries `lts` (series string) and `on_lts` (bool | None) per entry, sourced from `load_lts_registry()` (built-in `_DEFAULT_LTS` = `{django: 4.2, python: 3.12}` + `SBOM_LTS_REGISTRY`). This story adds endoflife.date as an additional, broader source **below** the explicit registry in precedence. `_is_on_lts` and `_classify_currency`'s LTS-aware branch are unchanged — only the source of the `lts` series expands. [Source: backend/generate_sbom/analysis/services/versions.py]

### HTTP session pattern (AD)

Reuse `CachedLimiterSession` + `external_retry` from `analysis/services/http.py` (as OSV/PyPI/NVD do) so lookups are cached and rate-limited. Product data is small and rarely changes; a long cache TTL is appropriate. [Source: backend/generate_sbom/analysis/services/http.py]

### Name→product mapping

endoflife.date slugs are not always the PyPI name (e.g. many map 1:1: `django`, `numpy`, `python`; some differ). Ship a small curated map for the common mismatches and treat any unmapped/404 product as untracked — correctness over coverage (never assert a wrong LTS). The map can grow over time.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.1: Broaden LTS Coverage via endoflife.date]
- [Source: prd.md#FR-5.4 — Version currency + LTS]
- [Source: backend/generate_sbom/analysis/services/versions.py]
- [Source: backend/generate_sbom/analysis/services/http.py]
- [Source: https://endoflife.date/docs/api]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

### Completion Notes List

- **HTTP session:** new `http.eol_session()` (CachedLimiterSession, 7-day cache, 2 req/s). `build_session` gained an `allowable_codes` param; the eol session caches `404`s too, so the many untracked packages don't re-hit the API every run.
- **Lookup:** `versions._eol_lts_series(session, name)` queries `endoflife.date/api/{product}.json`, treats any truthy `lts` field (boolean `true` or a start-date string) as an LTS cycle, and returns the highest such `cycle`. Network/parse errors and untracked products fall through to `None` — never a fabricated LTS. A small `_EOL_PRODUCTS` map covers name↔slug mismatches; unmapped names try the normalized name and 404 to untracked.
- **Precedence (AC #5):** `classify` now resolves `lts = registry.get(name) or _eol_lts_series(...)` — the explicit built-in/`SBOM_LTS_REGISTRY` entry wins; endoflife.date fills the long tail. `on_lts`/currency are unchanged, just fed a broader `lts`.
- **Frontend:** none needed — the Versions tab (PR #42) already renders `lts`/`on_lts`; this only widens their source.
- **Tests:** endoflife.date drives the LTS series (latest LTS cycle, boolean+date forms); registry overrides the API; API error → untracked; name→slug mapping. Existing currency tests given their own `eol_session` for isolation/speed.
- Gate: `pixi run ci` exits 0 — backend 216 tests (94.11%), frontend 43.

### File List

- backend/generate_sbom/analysis/services/http.py (eol_session + allowable_codes)
- backend/generate_sbom/analysis/services/versions.py (_eol_lts_series, _EOL_PRODUCTS, classify precedence)
- backend/tests/unit/test_versions_service.py (endoflife.date tests + isolation)
