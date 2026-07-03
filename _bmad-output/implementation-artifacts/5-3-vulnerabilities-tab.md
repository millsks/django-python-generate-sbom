# Story 5.3: Vulnerabilities Tab

Status: ready-for-dev

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

### Debug Log References

### Completion Notes List

### File List
