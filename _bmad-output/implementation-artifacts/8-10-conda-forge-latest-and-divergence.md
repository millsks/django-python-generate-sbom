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
7. Given a package known by its PyPI name whose conda-forge package name differs (e.g. `torch` → `pytorch`), when its conda-forge latest is looked up, then a conda↔PyPI name mapping (parselmouth) resolves the correct conda-forge name; if the mapping has no entry, fall back to the same (normalized) name.
8. Given the name mapping, when it is used, then it is loaded from a locally-stored copy (no per-package network call for the mapping), refreshed periodically by a scheduled task, and its absence degrades gracefully (same-name fallback / `conda_latest: null`, never a crash).

## Tasks / Subtasks

- [ ] Task 1 — conda-forge HTTP session (AC: #4)
  - [ ] Add `conda_forge_session()` in `analysis/services/http.py` (CachedLimiterSession, cache TTL like PyPI, `allowable_codes=(200, 404)` to cache misses)
- [ ] Task 2 — conda↔PyPI name mapping via parselmouth (AC: #7, #8)
  - [ ] Add a mapping service that loads parselmouth's `compressed_mapping.json` from a **locally-stored** copy (object storage or a container path) — not a per-package network call — cached in memory per process
  - [ ] Expose `pypi_to_conda(name)` (and, for 8.8's use, `conda_to_pypi(name)`); PEP 503-normalize; unmapped → `None` (caller falls back to the same name)
  - [ ] Ship a bundled seed snapshot so first boot works offline; a missing/empty map degrades gracefully
  - [ ] Add a scheduled (celery beat) task that periodically refreshes the local copy from the parselmouth source; make the source URL + cadence configurable
- [ ] Task 3 — conda-forge latest lookup (AC: #1, #2, #7)
  - [ ] Add `_conda_forge_latest(session, name)` in `versions.py`: map the PyPI name → conda-forge name via the mapping service, then query **prefix.dev** for the conda-forge channel's latest version of that package (verify the exact prefix.dev API endpoint/query during implementation), returning the version string or `None`
  - [ ] Catch `requests.RequestException` / `ValueError` → `None` (never raise out of the phase), matching `_latest_version`
- [ ] Task 4 — Report fields (AC: #1, #3, #6)
  - [ ] In `classify`, add `conda_latest` and `latest_mismatch` to each entry; `latest_mismatch = bool(latest and conda_latest and latest != conda_latest)`
  - [ ] Leave `currency` / `_classify_currency` unchanged (PyPI-based)
- [ ] Task 5 — Frontend (AC: #5)
  - [ ] Add `conda_latest: string | null` and `latest_mismatch: boolean` to `VersionEntry` (`api/reports.ts`)
  - [ ] In `VersionsTab.tsx`, add a "conda-forge" latest column (or pair it with the Latest cell); when `latest_mismatch`, render the conda-forge value in an error/warning color with an accessible hint (e.g. title "behind the PyPI latest")
- [ ] Task 6 — Tests
  - [ ] Backend unit: conda-forge latest captured; divergence flagged when it differs from PyPI latest; equal versions → `latest_mismatch False`; not-on-conda-forge / API error → `conda_latest None`, no raise
  - [ ] Frontend: divergent row styles the conda-forge value distinctly; matching versions do not; null conda_latest shows a dash
  - [ ] `pixi run ci` exits 0 with ≥90% coverage on new code

## Dev Notes

### Data source — prefix.dev

The conda-forge latest version comes from **prefix.dev** (consistent with the
prefix.dev channel-explorer links in 8.9 and the parselmouth mapping below, also a
prefix-dev project) — not Anaconda.org. prefix.dev exposes package/channel metadata
via its API (GraphQL at `https://prefix.dev/api/graphql`, and/or a REST endpoint over
the `conda-forge` channel); the query returns the channel's available
versions/latest for a package. Verify the exact endpoint/query and the latest-version
field during implementation. Route it through the shared cached, rate-limited session
and cache 404s (like the endoflife.date session) — many PyPI packages have no
conda-forge counterpart.

### conda↔PyPI name mapping (parselmouth)

conda-forge package names frequently differ from their PyPI names (e.g. conda
`pytorch` ↔ PyPI `torch`), so looking up conda-forge by the PyPI name directly would
miss or mismatch. Use **parselmouth**'s mapping:

- **Source file:** `compressed_mapping.json` — raw at
  `https://raw.githubusercontent.com/prefix-dev/parselmouth/main/files/compressed_mapping.json`
  (repo: `prefix-dev/parselmouth`). Its native direction is conda-forge name → PyPI
  name; build the inverse (PyPI → conda) in memory for this story's lookup, and expose
  the forward direction for 8.8. A PyPI name may map from several conda names — pick a
  deterministic winner (or prefer an exact normalized match).
- **Store locally, don't look up per-name.** Load the file once per process into an
  in-memory map — do **not** hit the parselmouth GitHub Pages per-name endpoint
  (`https://prefix-dev.github.io/parselmouth/`) for every package. Persist a local copy
  (object storage or a container path) so all analysis workers share it.
- **Refresh periodically.** A celery beat task (this stack already runs `beat`) refreshes
  the local copy on a configurable cadence (e.g. weekly) so new/renamed packages are
  picked up. Ship a bundled seed snapshot so the first boot / offline case still works;
  a missing map degrades to same-name lookup (AC #7/#8).

[Source: https://prefix-dev.github.io/parselmouth/ ; https://github.com/prefix-dev/parselmouth/blob/main/files/compressed_mapping.json]

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
- [Source: https://prefix.dev/channels/conda-forge — conda-forge latest via prefix.dev API]
- [Source: https://github.com/prefix-dev/parselmouth/blob/main/files/compressed_mapping.json — conda↔PyPI name map]
- [Source: https://prefix-dev.github.io/parselmouth/ — parselmouth per-name lookup (alternative)]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
