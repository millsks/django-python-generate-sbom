# Story 8.12: Export Version Currency to Excel

Status: ready-for-dev

<!-- Establishes the shared Excel-export mechanism; 8.13/8.14 reuse it, 8.15 composes a combined workbook. -->

## Story

As a user,
I want to export the version-currency report to an Excel spreadsheet,
so that I can share and analyze it outside the app.

## Acceptance Criteria

1. Given the Version Currency tab, when I click an "Export to Excel" control, then a single-sheet `.xlsx` of the report downloads (e.g. `version-currency.xlsx`) (FR-E10).
2. Given the export, when it is produced, then the sheet has a header row and one row per package with the tab's columns (package, installed, latest, currency, LTS, on-LTS, ecosystem, and — once 8.10 lands — conda-forge latest / mismatch).
3. Given the tab has active filters/sort, when I export, then the export reflects the **full report** (all rows), not just the filtered/sorted view (documented choice; simplest + most complete).
4. Given the shared export mechanism, when it is built, then it is a reusable helper (one place that turns a report's rows + column spec into an `.xlsx`), so Stories 8.13 (vulnerabilities), 8.14 (licenses), and 8.15 (combined workbook) reuse it — no duplicated spreadsheet logic.
5. Given a report that failed/has no data, when the tab renders, then the export control is disabled or hidden (nothing to export).

## Tasks / Subtasks

- [ ] Task 1 — Shared Excel helper (AC: #1, #4)
  - [ ] Add a reusable export helper that builds a worksheet from `{ sheetName, columns: [{key,label}], rows }` and triggers a browser download; one workbook may hold multiple sheets (for 8.15)
  - [ ] Decide the generation approach (see Dev Notes): client-side (report JSON is already fetched) is the recommended default
- [ ] Task 2 — Version Currency export (AC: #1, #2, #3, #5)
  - [ ] Add an "Export to Excel" button to `VersionsTab.tsx`; map the report entries to the column spec; filename `version-currency.xlsx`
  - [ ] Disable/hide when the report failed or is empty
- [ ] Task 3 — Tests
  - [ ] Unit: the helper produces a workbook with the expected sheet name, header, and row count from sample rows
  - [ ] Frontend: the button is present when data exists, absent/disabled on failure/empty
  - [ ] `pixi run ci` exits 0

## Dev Notes

### Generation approach (decision to confirm at implementation)

**Recommended: client-side generation.** The report tabs already fetch the report JSON, so an in-browser library (e.g. `exceljs`) can build and download the `.xlsx` with no backend endpoint, no object-storage churn, and no artifact streaming (AD-11 is about not proxying stored artifacts). This keeps export logic beside display logic and is vitest-testable. Adds one frontend dependency (`exceljs` or similar) — flag it at implementation.

**Alternative: backend generation** (openpyxl → presigned download, mirroring the SBOM/graph 303 flow) — more pytest-testable and AD-11-consistent, but adds a runtime dependency (confirm per control constraints), an endpoint per report, and generate/store overhead. Choose one and apply it uniformly across 8.12–8.15.

### Full-report vs filtered

Export the whole report (AC #3) — filters/sort are a viewing aid; a shared spreadsheet should be complete. Revisit if users ask for "export current view".

### References

- [Source: frontend/src/components/VersionsTab.tsx, frontend/src/api/reports.ts]
- [Source: _bmad-output/implementation-artifacts/8-13-…, 8-14-…, 8-15-… (reuse this helper)]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
