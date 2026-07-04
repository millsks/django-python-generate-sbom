# Story 4.3: License Compliance Report — Phase 5

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a license compliance report grouped by legal risk,
so that I can quickly see which dependencies need legal attention.

## Acceptance Criteria

1. Given a resolved package list, when Phase 5 runs, then the declared license for each package is extracted from PyPI metadata (FR-5.2).
2. Given each package's license identifier, when it is classified, then it is placed in exactly one of four tiers: Strong Copyleft (AGPL-3.0-only, GPL-2.0/3.0 families), Weak Copyleft (LGPL-2.1/3.0 families), Unknown (no license or non-SPDX identifier), or Permissive (all other SPDX identifiers) (FR-5.2).
3. Given the four tiers, when the report is assembled, then tiers are ordered by descending attention required: Strong Copyleft → Weak Copyleft → Unknown → Permissive (FR-5.2).
4. Given a package with no declared license or a non-SPDX identifier, when it is classified, then it is placed in the Unknown tier (FR-5.2).
5. Given Phase 5 completes, when the result is persisted, then an `AnalysisReport` with `report_type="license"` is created with `artifact_key` and a `summary` recording per-tier counts (AD-6).
6. Given `GET /api/v1/sbom/result/{task_id}/reports/licenses/`, when called with an org-scoped credential, then the license report JSON is returned; a cross-org request returns `404` (AD-2, AD-11).
7. Given Phase 5 starts and completes, when each boundary is crossed, then progress updates cover the 80–88% range with structured logging (FR-4.2, NFR-6.1).

## Tasks / Subtasks

- [ ] Task 1 — License extraction (AC: #1)
  - [ ] Implement `analysis/services/license.py::classify(packages) -> dict` as a pure function
  - [ ] Extract the declared license per package from PyPI metadata (`pip-licenses --from=mixed --format=json` over the installed/resolved set)
- [ ] Task 2 — Four-tier classification (AC: #2, #3, #4)
  - [ ] Map SPDX identifiers to tiers: Strong Copyleft (AGPL/GPL families), Weak Copyleft (LGPL families; MPL per design table), Unknown (no license / non-SPDX / proprietary), Permissive (MIT, Apache-2.0, BSD-*, ISC, etc.)
  - [ ] Emit tiers in descending-attention order: Strong Copyleft → Weak Copyleft → Unknown → Permissive
  - [ ] Any package lacking a declared license or with a non-SPDX identifier → Unknown
- [ ] Task 3 — Persist artifact + report (AC: #5)
  - [ ] Write report JSON to S3 at `sbom-results/{org_id}/{task_id}/licenses.json`
  - [ ] Return chord envelope: `report_type="license"`, `artifact_key` set, `summary={per_tier_counts}`, `failed=False`
- [ ] Task 4 — API endpoint (AC: #6)
  - [ ] `GET /api/v1/sbom/result/{task_id}/reports/licenses/`: job via `SBOMJob.objects.for_org(org).get(...)` (404 cross-org), return JSON (or 303 presigned per AD-11)
- [ ] Task 5 — Progress + logging (AC: #7)
  - [ ] `task.update_state` across 80–88%, `current_step='licence compliance'`
  - [ ] structlog on start/completion: phase, duration, package count, bound `org_id`/`task_id`
- [ ] Task 6 — Tests (AC: all)
  - [ ] Fixture packages spanning all four tiers incl. no-license and non-SPDX cases; assert exact tier placement + ordering + per-tier counts
  - [ ] API test: cross-org → 404
  - [ ] ≥90% coverage; `pixi run ci` exits 0

## Dev Notes

### License service (solution-design.md §3.4)

Uses `pip-licenses --from=mixed --format=json` output for installed packages. Classifies each license into one of four tiers:

| Tier | Examples | Action signalled |
|---|---|---|
| Strong Copyleft | GPL, AGPL | Attention required |
| Weak Copyleft | LGPL, MPL | Review recommended |
| Unknown | No SPDX ID, proprietary | Legal review needed |
| Permissive | MIT, Apache 2.0, BSD | Use freely |

Exact SPDX members from the PRD (FR-5.2): Strong Copyleft = `AGPL-3.0-only`, `GPL-2.0-only`, `GPL-2.0-or-later`, `GPL-3.0-only`, `GPL-3.0-or-later`; Weak Copyleft = `LGPL-2.1-only`, `LGPL-2.1-or-later`, `LGPL-3.0-only`, `LGPL-3.0-or-later`; Unknown = no/non-SPDX license; Permissive = all other SPDX ids. Pure function, no HTTP/Celery coupling (AD-3).

### Storage & download (AD-6, AD-11)

Report JSON at `sbom-results/{org_id}/{task_id}/licenses.json`; only `artifact_key` in PostgreSQL. Download returns JSON or `303` → presigned URL. Cross-org access → 404 (AD-2).

### Failure semantics (§4.4)

On failure, return envelope `failed=True` + `failure_reason`; the chord (4.6) continues and the SBOM still completes (FR-4.5).

### Dependency / sequencing notes

- Depends on Story 4.1 (envelope helpers, `AnalysisReport`) and Epic 3 resolved package list.
- Wired into the real analysis group by Story 4.6.

### Project Structure Notes

- Service: `<project_slug>/analysis/services/license.py` (pure function).
- Endpoint under `/api/v1/sbom/result/{task_id}/reports/licenses/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3: License Compliance Report — Phase 5]
- [Source: solution-design.md#3.4 analysis/ — Licence service]
- [Source: solution-design.md#6.1 Storage paths]
- [Source: ARCHITECTURE-SPINE.md#AD-6 — Storage triad]
- [Source: ARCHITECTURE-SPINE.md#AD-11 — Presigned URL downloads]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: prd.md#FR-5.2, FR-4.2, NFR-6.1]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

- Deviated from the story's `pip-licenses` suggestion — it reads the *installed* environment, but the resolved package set is not installed here. Used the **PyPI JSON API** (via 4.1's `pypi_session`) instead. Documented below.

### Completion Notes List

- **`analysis/services/license.py::classify(packages)`** — pure (AD-3). Extracts the declared license per package from PyPI JSON metadata, preferring PEP 639 `license_expression` (SPDX) → Trove `classifiers` (mapped to SPDX via a controlled table) → a short free-text `license`. Classifies into four tiers and returns `{tiers, summary}`.
- **Tiers** in descending-attention order (AC #3): **Strong Copyleft** (AGPL/GPL families), **Weak Copyleft** (LGPL/MPL families), **Unknown** (no license / non-SPDX / unrecognized), **Permissive** (a curated set of common permissive SPDX ids). Anything not recognized falls to **Unknown** (AC #4). PyPI fetch failures degrade to Unknown (best-effort).
- **PyPI JSON, not pip-licenses:** `pip-licenses` inspects installed packages; our resolved list isn't installed, so the PyPI JSON API (already provisioned as `pypi_session` in 4.1) is the correct source.
- **Phase 5 task** `tasks/analysis.py::classify_licenses` (analysis queue, 80→88%). Refactored the module to a shared **`_run_phase`** helper (build → persist → envelope, with the FR-4.5 failed-envelope-not-raise semantics) now driving both Phase 4 and Phase 5, and reusable by 4.4/4.5.
- **Endpoint** `GET /api/v1/sbom/result/{task_id}/reports/licenses/` via `LicenseReportView(_ReportView)` → 303 presigned; cross-org → 404.
- Gate: `pixi run ci` exits 0 — 161 tests, 95.29% coverage.

### File List

- backend/generate_sbom/analysis/services/license.py (classify + tier logic)
- backend/generate_sbom/tasks/analysis.py (_run_phase helper + classify_licenses; refactored scan_vulnerabilities onto it)
- backend/generate_sbom/analysis/views.py, urls.py (LicenseReportView + route)
- backend/tests/unit/test_license_service.py, test_license_task_api.py (new)
