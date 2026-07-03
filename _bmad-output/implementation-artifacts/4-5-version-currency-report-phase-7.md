# Story 4.5: Version Currency Report — Phase 7

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a version currency report,
so that I can see which dependencies are outdated and by how much.

## Acceptance Criteria

1. Given a resolved package list, when Phase 7 runs, then the latest stable version of each package is fetched from the PyPI JSON API (FR-5.4).
2. Given an installed version and the latest version, when currency is classified, then it is one of: `current` (same release series), `behind-1` (one series behind), `behind-2+` (two or more series behind, including major-version gaps), or `unknown` (version data unavailable) (FR-5.4).
3. Given a package tracked in the LTS registry (Django, Python, plus any operator additions), when its currency is classified, then LTS-aware classification is applied using the known LTS version (FR-5.4).
4. Given the `SBOM_LTS_REGISTRY` environment variable containing a JSON mapping of package name to LTS version string, when the service loads the registry, then operator-supplied entries extend or override the built-in defaults (FR-5.4).
5. Given Phase 7 completes, when the result is persisted, then an `AnalysisReport` with `report_type="version"` is created with `artifact_key` and a `summary` recording counts per currency class (AD-6).
6. Given `GET /api/v1/sbom/result/{task_id}/reports/versions/`, when called with an org-scoped credential, then the version currency report JSON is returned; a cross-org request returns `404` (AD-2, AD-11).
7. Given Phase 7 starts and completes, when each boundary is crossed, then progress updates cover the 93–97% range with structured logging (FR-4.2, NFR-6.1).

## Tasks / Subtasks

- [ ] Task 1 — Fetch latest versions from PyPI (AC: #1)
  - [ ] Implement `analysis/services/versions.py::classify(packages) -> dict` as a pure function using the shared cached/rate-limited session (Story 4.1)
  - [ ] Fetch `/pypi/{package}/json` (1h Redis cache `pypi-cache:{package}`, 5 req/s); read `info.version` for latest stable
- [ ] Task 2 — Classify currency by release-series distance (AC: #2)
  - [ ] Use `packaging` (PEP 440) to sort/compare versions
  - [ ] Classify: `current` (same release series), `behind-1` (one series behind), `behind-2+` (two+ series behind incl. major gaps), `unknown` (no data)
- [ ] Task 3 — LTS-aware classification (AC: #3, #4)
  - [ ] Load the LTS registry: built-in defaults for Django and Python, overridable/extendable via `SBOM_LTS_REGISTRY` (JSON file path or inline JSON mapping name→LTS version string)
  - [ ] For registry-tracked packages, apply LTS-aware classification using the known LTS version
- [ ] Task 4 — Persist report (AC: #5)
  - [ ] Write report JSON to S3 at `sbom-results/{org_id}/{task_id}/versions.json`
  - [ ] Return chord envelope: `report_type="version"`, `artifact_key` set, `summary={counts_per_currency_class}`, `failed=False`
- [ ] Task 5 — API endpoint (AC: #6)
  - [ ] `GET /api/v1/sbom/result/{task_id}/reports/versions/`: job via `for_org` (404 cross-org), return JSON (or 303 presigned per AD-11)
- [ ] Task 6 — Progress + logging (AC: #7)
  - [ ] `task.update_state` across 93–97%, `current_step='version currency'`
  - [ ] structlog on start/completion: phase, duration, package count
- [ ] Task 7 — Tests (AC: all)
  - [ ] `respx`-mocked PyPI responses; assert each currency class incl. major-gap → `behind-2+` and missing-data → `unknown`
  - [ ] LTS registry: default + `SBOM_LTS_REGISTRY` override both exercised
  - [ ] API test: cross-org → 404
  - [ ] ≥90% coverage; `pixi run ci` exits 0

## Dev Notes

### Version currency service (solution-design.md §3.4; FR-5.4)

Fetches `/pypi/{package}/json` from the PyPI JSON API (cached 1h in Redis via `requests-cache`, 5 req/s). Compares installed to latest using PEP 440 sort via `packaging`. Classifies by release-series distance.

PRD currency classes (FR-5.4) — authoritative:
- `current` — same release series as latest (e.g. 5.2.1 vs 5.2.3)
- `behind-1` — one release series behind (e.g. 5.1.x when 5.2.x is latest)
- `behind-2+` — two or more release series behind, including major-version gaps (e.g. 4.x when 5.2.x latest)
- `unknown` — version data unavailable

Note: the solution-design table lists a finer-grained breakdown (patch/minor/major behind, pre-release); the PRD's four classes (`current`/`behind-1`/`behind-2+`/`unknown`) are the required output contract for the report and UI (FR-5.4, FR-6.6). Implement the four PRD classes; internal finer detail may inform them but the report exposes the four.

### LTS registry (FR-5.4; solution-design.md §8)

`SBOM_LTS_REGISTRY` env var — JSON file path or inline JSON mapping package name → LTS version string. Built-in defaults ship for Django and Python. Operator entries extend or override defaults. LTS-tracked packages get LTS-aware classification.

### Storage & download (AD-6, AD-11)

Report JSON at `sbom-results/{org_id}/{task_id}/versions.json`; only `artifact_key` in PostgreSQL. Download returns JSON or `303` → presigned URL. Cross-org → 404 (AD-2).

### Failure semantics (§4.4)

On failure (after `tenacity` retries), envelope `failed=True` + `failure_reason`; chord (4.6) continues; SBOM still completes (FR-4.5).

### Dependency / sequencing notes

- Depends on Story 4.1 (shared HTTP session, envelope helpers, `AnalysisReport`) and Epic 3 resolved package list.
- The Version Currency SPA tab (Epic 5 Story 5.6) consumes this report's four classes.
- Wired into the real analysis group by Story 4.6.

### Project Structure Notes

- Service: `<project_slug>/analysis/services/versions.py` (pure function).
- Endpoint under `/api/v1/sbom/result/{task_id}/reports/versions/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5: Version Currency Report — Phase 7]
- [Source: solution-design.md#3.4 analysis/ — Version currency service]
- [Source: solution-design.md#6.1 Storage paths, #6.3 Redis usage]
- [Source: solution-design.md#8. Configuration — SBOM_LTS_REGISTRY]
- [Source: ARCHITECTURE-SPINE.md#AD-6 — Storage triad]
- [Source: ARCHITECTURE-SPINE.md#AD-11 — Presigned URL downloads]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: prd.md#FR-5.4, FR-4.2, NFR-6.1]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
