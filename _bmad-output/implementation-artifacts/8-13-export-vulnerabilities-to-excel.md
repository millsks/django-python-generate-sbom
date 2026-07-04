# Story 8.13: Export Vulnerabilities to Excel

Status: review

<!-- Reuses the shared Excel-export helper from Story 8.12. -->

## Story

As a user,
I want to export the vulnerabilities report to an Excel spreadsheet,
so that I can triage and share findings outside the app.

## Acceptance Criteria

1. Given the Vulnerabilities tab, when I click "Export to Excel", then a single-sheet `vulnerabilities.xlsx` downloads (FR-E10).
2. Given the export, when produced, then rows carry the tab's columns — package, installed version, CVE/GHSA id(s), CVSS score, severity, CWE, advisory URL — one row per finding, covering the full report (all severities/filters).
3. Given the shared export helper (Story 8.12), when this export is built, then it reuses that helper — no duplicated spreadsheet logic.
4. Given a failed/empty vulnerability report, when the tab renders, then the export control is disabled/hidden.

## Tasks / Subtasks

- [ ] Task 1 — Vulnerabilities export (AC: #1, #2, #3, #4)
  - [ ] Add an "Export to Excel" button to `VulnerabilitiesTab.tsx` using the shared helper; map findings to the column spec; filename `vulnerabilities.xlsx`
  - [ ] One row per finding (flatten multi-id / multi-CWE consistently with the table); disable/hide on failure/empty
- [ ] Task 2 — Tests
  - [ ] Frontend: button present with data, absent/disabled on failure/empty; row/column mapping covered by the helper's unit test
  - [ ] `pixi run ci` exits 0

## Dev Notes

Reuses the export mechanism and full-report semantics established in Story 8.12 (see its Dev Notes for the client-side-vs-backend decision — apply the same one here). Match the tab's flattening: if a package has multiple advisory ids/CWEs, mirror how the table renders them (comma-joined or one row per id — pick one and keep it consistent across the export). [Source: frontend/src/components/VulnerabilitiesTab.tsx]

### References

- [Source: _bmad-output/implementation-artifacts/8-12-export-version-currency-to-excel.md]
- [Source: frontend/src/components/VulnerabilitiesTab.tsx, frontend/src/api/reports.ts]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

### Completion Notes List

- Reused the Story 8.12 shared export helper (`excelExport.ts`, left untouched) and added a `vulnerabilitiesSheet(report)` builder to `reportSheets.ts` in the same style as `versionCurrencySheet`, keeping the mapping reusable by the future Overview combined workbook (8.15).
- Added an "Export to Excel" button to `VulnerabilitiesTab.tsx` that calls `downloadWorkbook(buildWorkbook([vulnerabilitiesSheet(report)]), 'vulnerabilities.xlsx')`. The button lives in the loaded-report render path only, so it is absent on failed/empty reports (AC #4).
- Columns: Package, Installed, CVE / GHSA, CVSS, Severity, CWE, Advisory URL. One row per finding across the FULL report (all severities, independent of the active severity filter). Multi-id cells dedupe id + aliases and multi-CWE cells comma-join, mirroring `VulnerabilitiesTab.toRows`. Null CVSS and empty CWE render as ''.
- Tests: `vulnerabilitiesSheet` mapping test in `reportSheets.test.ts`; `VulnerabilitiesTab.test.tsx` verifies the button triggers `downloadWorkbook` with `vulnerabilities.xlsx` (mocking `../excelExport`) and that the button is absent on failed and empty reports.
- `pixi run ci` exits 0.

### File List

- frontend/src/reportSheets.ts (modified)
- frontend/src/reportSheets.test.ts (modified)
- frontend/src/components/VulnerabilitiesTab.tsx (modified)
- frontend/src/components/VulnerabilitiesTab.test.tsx (modified)
- _bmad-output/implementation-artifacts/8-13-export-vulnerabilities-to-excel.md (modified)
