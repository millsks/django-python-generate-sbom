# Story 8.14: Export Licenses to Excel

Status: ready-for-dev

<!-- Reuses the shared Excel-export helper from Story 8.12. -->

## Story

As a user,
I want to export the license report to an Excel spreadsheet,
so that I can review license compliance outside the app.

## Acceptance Criteria

1. Given the Licenses tab, when I click "Export to Excel", then a single-sheet `licenses.xlsx` downloads (FR-E10).
2. Given the export, when produced, then rows carry the tab's columns — package, license (identifier/expression), risk tier (permissive/copyleft/unknown) — one row per package, covering the full report.
3. Given the shared export helper (Story 8.12), when this export is built, then it reuses that helper — no duplicated spreadsheet logic.
4. Given a failed/empty license report, when the tab renders, then the export control is disabled/hidden.

## Tasks / Subtasks

- [ ] Task 1 — Licenses export (AC: #1, #2, #3, #4)
  - [ ] Add an "Export to Excel" button to `LicensesTab.tsx` using the shared helper; map entries to the column spec; filename `licenses.xlsx`
  - [ ] Disable/hide on failure/empty
- [ ] Task 2 — Tests
  - [ ] Frontend: button present with data, absent/disabled on failure/empty
  - [ ] `pixi run ci` exits 0

## Dev Notes

Reuses the export mechanism and full-report semantics from Story 8.12 (apply the same generation approach). Match the tab's column set and risk-tier labeling. [Source: frontend/src/components/LicensesTab.tsx]

### References

- [Source: _bmad-output/implementation-artifacts/8-12-export-version-currency-to-excel.md]
- [Source: frontend/src/components/LicensesTab.tsx, frontend/src/api/reports.ts]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
