# Story 8.10: Capture conda-forge Latest & Flag PyPI/conda-forge Divergence

Status: ready-for-dev

<!-- Refines 8.8's "conda currency stays PyPI-derived" note: we now capture conda-forge latest for comparison. -->

## Story

As a user,
I want the version-currency report to show the latest version on both PyPI and conda-forge and highlight when they differ,
so that I can see when conda-forge packaging is behind the PyPI release.

The currency *classification* (current/behind) stays PyPI-based; conda-forge latest is
an additional informational value with divergence highlighting.

## Acceptance Criteria

1. Given a package in the version-currency report, when it is built, then the entry includes `conda_latest` (the latest conda-forge version) alongside the existing PyPI `latest` (FR-E8).
2. Given a package not published on conda-forge, or the API is unreachable / returns bad JSON, when conda-forge latest is looked up, then `conda_latest` is `null` and the phase never crashes.
3. Given both PyPI `latest` and `conda_latest` are known, when they are not equal, then the entry flags divergence (`latest_mismatch: true`); otherwise `false`.
4. Given conda-forge lookups, when performed, then they go through the shared cached, rate-limited session pattern (like PyPI/endoflife.date), caching 404 misses so untracked packages don't re-hit the API.
5. Given the Version Currency tab, when a row renders, then it shows the conda-forge latest; and when it diverges from the PyPI latest, the conda-forge value is visually signified (error/warning color) to indicate conda-forge is out of step.
6. Given the currency classification, when computed, then it remains PyPI-based — this story does not reclassify currency against conda-forge (out of scope).

## Tasks / Subtasks

- [ ] Task 1 — conda-forge HTTP session (AC: #4)
  - [ ] Add `conda_forge_session()` in `analysis/services/http.py` (CachedLimiterSession, cache TTL like PyPI, `allowable_codes=(200, 404)` to cache misses)
- [ ] Task 2 — conda-forge latest lookup (AC: #1, #2)
  - [ ] Add `_conda_forge_latest(session, name)` in `versions.py` querying the conda-forge metadata API (`https://api.anaconda.org/package/conda-forge/{name}` → `latest_version`; verify field/host during implementation), returning the version string or `None`
  - [ ] Catch `requests.RequestException` / `ValueError` → `None` (never raise out of the phase), matching `_latest_version`
- [ ] Task 3 — Report fields (AC: #1, #3, #6)
  - [ ] In `classify`, add `conda_latest` and `latest_mismatch` to each entry; `latest_mismatch = bool(latest and conda_latest and latest != conda_latest)`
  - [ ] Leave `currency` / `_classify_currency` unchanged (PyPI-based)
- [ ] Task 4 — Frontend (AC: #5)
  - [ ] Add `conda_latest: string | null` and `latest_mismatch: boolean` to `VersionEntry` (`api/reports.ts`)
  - [ ] In `VersionsTab.tsx`, add a "conda-forge" latest column (or pair it with the Latest cell); when `latest_mismatch`, render the conda-forge value in an error/warning color with an accessible hint (e.g. title "behind the PyPI latest")
- [ ] Task 5 — Tests
  - [ ] Backend unit: conda-forge latest captured; divergence flagged when it differs from PyPI latest; equal versions → `latest_mismatch False`; not-on-conda-forge / API error → `conda_latest None`, no raise
  - [ ] Frontend: divergent row styles the conda-forge value distinctly; matching versions do not; null conda_latest shows a dash
  - [ ] `pixi run ci` exits 0 with ≥90% coverage on new code

## Dev Notes

### Data source

conda-forge's per-package latest is available from the Anaconda.org metadata API:
`GET https://api.anaconda.org/package/conda-forge/{name}` returns JSON including
`latest_version`. Simple, documented, and fits the existing cached/rate-limited
session pattern. prefix.dev's API is an alternative if Anaconda.org proves
unsuitable. Verify the exact host/field during implementation. Cache 404s (like the
endoflife.date session) — many PyPI packages have no conda-forge counterpart.

### Scope boundary

Only the *display* of divergence is in scope — currency classification
(current/behind-1/behind-2+) stays PyPI-based. Reclassifying currency against
conda-forge (e.g. a conda package that is current on conda-forge but "behind" on
PyPI) is a deliberate future story, not this one. [Source: epics.md#Story 8.10]

### Relationship to 8.8 / 8.9

Independent of the ecosystem flag (8.8) and links (8.9) — this fetches conda-forge
latest for comparison regardless of a package's declared source. It supersedes 8.8's
"Conda currency stays PyPI-derived / out of scope" note by adding the conda-forge
latest (though currency classification still stays PyPI-based).

### Cost

Adds one conda-forge lookup per package (cached, rate-limited). On a cold cache this
roughly matches the existing PyPI-latest call volume; caching + 404-caching keep
repeat runs and untracked packages cheap.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.10]
- [Source: backend/generate_sbom/analysis/services/versions.py — _latest_version, classify]
- [Source: backend/generate_sbom/analysis/services/http.py — session pattern]
- [Source: frontend/src/components/VersionsTab.tsx, frontend/src/api/reports.ts]
- [Source: https://api.anaconda.org/package/conda-forge/ — conda-forge latest_version]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
