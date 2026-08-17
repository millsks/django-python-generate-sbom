# Story 21.14: Vulnerabilities Tab

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.13**. Third tab of the results shell.

## Story

As a user,
I want a sortable, severity-filterable table of vulnerable packages,
so that I can triage my dependencies' security findings.

## Acceptance Criteria

1. **The table is converted.**
   Given `VulnerabilitiesTab.tsx` renders "a sortable, severity-filterable table of vulnerable packages", when
   it is converted, then a django-tables2 table with a django-filter severity filter renders the same columns,
   the same severity ordering, and the same outbound advisory links (OSV/CVE, with the NVD CWE enrichment from
   Epic 4), with sorting and filtering carried in the querystring.
2. **The default sort is preserved.**
   Given Story 8.16 set a default sort order per tab, when the table renders with no explicit sort, then it
   matches the SPA's default.
3. **A clean scan shows an explicit zero-state.**
   Given the SPA shows "an explicit zero-state rather than an empty table", when no vulnerabilities were found,
   then the tab states that the scan found none — visibly distinct from "no data available".
4. **A failed phase shows the shared notice.**
   Given analysis phases fail independently (FR-6.7) and the SPA renders `TabFailureNotice` with the recorded
   reason, when the vulnerability phase has failed, then the tab shows the same failure notice with its reason
   instead of an empty or zero result.
5. **Gate green.**
   When the story completes, then tests cover sorting, severity filtering, the default sort, the zero-state,
   and the failed-phase notice, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — `VulnerabilityTable` (AC: #1, #2)** — Columns, severity ordering, advisory links.
- [ ] **Task 2 — Severity `FilterSet` (AC: #1)** — Querystring-driven.
- [ ] **Task 3 — Zero-state vs. no-data (AC: #3)** — Two distinct states; do not collapse them.
- [ ] **Task 4 — Failure notice partial (AC: #4)** — Shared with Stories 21.15 and 21.16.
- [ ] **Task 5 — Tests + gate (AC: #5)**.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/components/VulnerabilitiesTab.tsx:1-4` header comment — "a sortable, severity-filterable table
  of vulnerable packages. Fetches the report JSON (served inline by the backend); a failed phase shows the
  shared `TabFailureNotice`, and a clean scan shows an explicit zero-state rather than an empty table."
- Failure detection pattern (shared across tabs): the report request raises `ApiError` with
  `code === 'report_failed'` carrying `failureReason`; the tab renders `TabFailureNotice` with it.
- `frontend/src/api/reports.ts` — `getVulnerabilities(taskId)`; the analysis chord result shape is
  `{report_type, artifact_key, summary, failed, failure_reason}`.
- Epic 4 built the report: OSV findings plus NVD CWE enrichment (Story 4.2).
- Excel export is Story 8.13 — reimplemented server-side in **Story 21.17**, not here.

### Three distinct empty-ish states

There are three, and conflating any two of them is the likeliest defect: **clean scan** (report ran, found
nothing), **no data** (report absent), and **failed phase** (report errored, with a reason). The SPA
distinguishes all three; so must this.

### The shared failure notice starts here

`TabFailureNotice` is used by Stories 21.14, 21.15, and 21.16. Build it as a reusable partial in this story and
reuse it in the next two rather than copying it.

### Testing standards

- One test per empty-ish state, asserting the rendered text differs.
- A test asserting severity filtering is reflected in the querystring and survives a refresh.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.14: Vulnerabilities Tab]
- `frontend/src/components/{VulnerabilitiesTab,TabFailureNotice}.tsx`, `frontend/src/api/reports.ts`,
  `generate_sbom/analysis/services/vulnerability.py`.
- Upstream: `21-13-sbom-viewer-tab.md`. Downstream: `21-15`, `21-16` (reuse the failure partial), `21-17`.

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
