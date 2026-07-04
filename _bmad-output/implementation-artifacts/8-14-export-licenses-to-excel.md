# Story 8.14: Export Licenses to Excel

Status: review

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

claude-opus-4-8[1m]

### Debug Log References

### Completion Notes List

- Reuses the Story 8.12 shared export helper (`excelExport.ts`, untouched) via a new `licensesSheet(report)` builder in `reportSheets.ts` — same style as `versionCurrencySheet`/`vulnerabilitiesSheet`, so 8.15's Overview workbook can reuse it.
- `licensesSheet` flattens one row per package across every tier (columns: Package, Installed, License, Risk Tier); empty tiers contribute no rows; covers the full report.
- Added an "Export to Excel" button to `LicensesTab.tsx` (in the tier-controls `Stack`, right-aligned via `ml: auto`) that downloads `licenses.xlsx`. It's gated by `report.tiers.length > 0`, so it's absent on empty reports and on the failure/loading paths (early returns) — satisfying AC #4. No new dependencies.
- Tests: `licensesSheet` mapping (flatten + tier + empty-tier skip) in `reportSheets.test.ts`; LicensesTab export-triggers-`downloadWorkbook`-with-`licenses.xlsx`, and export control absent when there are no tiers.
- Gate: `pixi run ci` exits 0 — backend 262 (93.90%), frontend 71 (14 files).

### File List

- frontend/src/reportSheets.ts (licensesSheet builder)
- frontend/src/reportSheets.test.ts (licensesSheet test)
- frontend/src/components/LicensesTab.tsx (Export to Excel button)
- frontend/src/components/LicensesTab.test.tsx (export + hidden-when-empty tests)
