# Story 5.3: Vulnerabilities Tab

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a sortable, filterable table of vulnerable packages,
so that I can prioritize which dependencies to address.

## Acceptance Criteria

1. Given a job with vulnerability findings, when I view the Vulnerabilities tab, then a table lists package name, installed version, CVE/GHSA IDs, CVSS score, severity (Critical/High/Medium/Low), and an advisory link.
2. Given the vulnerabilities table, when I click a column header, then the table sorts by that column; severity sorts by rank (Critical highest).
3. Given the vulnerabilities table, when I apply a severity filter, then only rows matching the selected severity are shown.
4. Given a job with zero vulnerabilities, when I view the tab, then it explicitly displays "No vulnerabilities found in X packages" rather than an empty table.
5. Given the vulnerability phase failed, when I view the tab, then a failure notice with the reason is shown.

## Tasks / Subtasks

- [ ] Task 1 — Fetch report (AC: #1)
  - [ ] Call `api/reports.getVulnerabilities(taskId)` → `GET /api/v1/sbom/result/{taskId}/reports/vuln/` (JSON)
  - [ ] Type the response: per-package entries with name, installed version, CVE/GHSA id(s), CVSS score, severity, advisory URL, CWE (where enriched)
- [ ] Task 2 — Table UI (AC: #1)
  - [ ] MUI table with columns: package, installed version, CVE/GHSA IDs, CVSS, severity, advisory link (opens OSV advisory in a new tab)
- [ ] Task 3 — Sorting (AC: #2)
  - [ ] Column-header sort for all columns; severity sorts by rank Critical > High > Medium > Low (not alphabetically)
- [ ] Task 4 — Severity filter (AC: #3)
  - [ ] Filter control (Critical/High/Medium/Low, multi or single) that narrows visible rows
- [ ] Task 5 — Zero-finding state (AC: #4)
  - [ ] When the report has no vulnerable packages, render "No vulnerabilities found in X packages" (X = total scanned, from summary) — not an empty table
- [ ] Task 6 — Failure notice (AC: #5)
  - [ ] If the vuln report `failed`, render the shared `TabFailureNotice` with `failure_reason` (from 5.1)
- [ ] Task 7 — Tests (AC: #2, #3, #4, #5)
  - [ ] Sort-by-severity orders Critical first
  - [ ] Severity filter hides non-matching rows
  - [ ] Zero-finding renders the explicit message with the scanned count
  - [ ] Failed report renders the failure notice

## Dev Notes

### Report shape (solution-design.md §3.4 vulnerability service, §5.2)

Vulnerability report served at `GET /api/v1/sbom/result/{taskId}/reports/vuln/`. Backed by the OSV batch API with NVD CWE enrichment (Epic 4 Story 4.2). Only vulnerable packages are listed (clean packages omitted); the "X packages" in the zero-state comes from the scanned total in the job summary. Severity ∈ {Critical, High, Medium, Low}; CVSS score present where available; advisory link points to the OSV advisory. [Source: solution-design.md §3.4; epics.md#Story 4.2]

### Severity ranking

Sort severity by rank, not lexically: Critical(4) > High(3) > Medium(2) > Low(1). [Source: epics.md#Story 5.3]

### Conventions

- Fetch via `frontend/src/api/reports.ts` — no `fetch` in the component (AD-5).
- MUI 9.1.2 table components. [Source: solution-design.md §7.1]

### Dependency / sequencing

Depends on Story 5.1 (shell + api layer) and consumes the Epic 4 Story 4.2 vuln endpoint. Independent of other tabs. [Source: epics.md#Epic 5]

### Project Structure Notes

- Vulnerabilities tab panel under `frontend/src/pages/`/`components/`; fetcher in `frontend/src/api/reports.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3: Vulnerabilities Tab]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA: REST API only]
- [Source: solution-design.md#3.4 analysis/ — Vulnerability service]
- [Source: solution-design.md#5.2 Endpoint inventory]
- [Source: prd.md#FR-6.3, FR-6.7]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

- Endpoint name: the story lists `/reports/vuln/`; the built path is `/reports/vulnerabilities/`.
- Frontend test gotcha (cost ~an hour): `beforeEach(mockReset())` on a mock later given `mockRejectedValue` makes vitest report a false "unhandled rejection" and fail the test. Fix: set the mock implementation per-test, no `mockReset`. Saved to memory [[vitest-mockreset-rejected-promise]].

### Completion Notes List

- **Backend — inline JSON (the deferred 5.1 decision):** the vuln/license/version report endpoints now serve the report **JSON inline (200)** instead of 303-to-presigned. Split the view base into `_JsonReportView` (reads the artifact from storage, returns JSON) and `_PresignedDownloadView` (303 — kept for the genuine file download, the graph SVG). The graph JSON endpoint (served from `summary`) and the SBOM result 303 are unchanged. Updated the three affected endpoint tests (now assert 200 + JSON).
- **`VulnerabilitiesTab`** (new): fetches `getVulnerabilities`, renders an MUI table (package, version, CVE/GHSA, CVSS, severity, advisory link opening OSV in a new tab). **Column sort** (severity by **rank** Critical>High>Medium>Low, not lexical); **severity filter**; **zero-state** ("No vulnerabilities found in X packages", X from the scanned total); **failure notice** via the shared `TabFailureNotice` when the report `failed` (surfaced through `ApiError.code === 'report_failed'` + `failureReason`). Lazy-mounted (fetches only when the tab is opened, via the shell's `TabPanel`).
- Wired into `ResultsPage` (tab index 1), passed the scanned total from `summary_stats.total_packages`.
- **Tests:** backend inline-JSON endpoints; frontend — severity-rank sort, severity filter, zero-state with count, failure notice.
- Gate: `pixi run ci` exits 0 — backend 177 tests (95.26%), frontend 12 tests.

### File List

- backend/generate_sbom/analysis/views.py (_JsonReportView / _PresignedDownloadView split)
- backend/tests/unit/test_vulnerability_task_api.py, test_license_task_api.py, test_versions_task_api.py (inline-JSON assertions)
- frontend/src/components/VulnerabilitiesTab.tsx (new) + VulnerabilitiesTab.test.tsx (new)
- frontend/src/pages/ResultsPage.tsx (wires the Vulnerabilities tab)
