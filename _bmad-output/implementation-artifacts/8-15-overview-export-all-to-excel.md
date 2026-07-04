# Story 8.15: Overview — Export All Reports to a Single Excel Workbook

Status: review

<!-- Composes the per-report exports (8.12/8.13/8.14) into one workbook. -->

## Story

As a user,
I want a single "Export to Excel" on the Overview tab that produces one workbook with every report,
so that I can grab the whole analysis in one file.

## Acceptance Criteria

1. Given the Overview tab of a completed job, when I click "Export all to Excel", then one `.xlsx` downloads (e.g. `sbom-report.xlsx`) containing a sheet per report — **Version Currency**, **Vulnerabilities**, **Licenses** (FR-E10).
2. Given each sheet, when written, then it matches the corresponding per-tab export's columns/rows (reuses the same helper + column specs as 8.12/8.13/8.14 — no divergence between the per-tab file and its sheet in the combined workbook).
3. Given a report that failed, when the workbook is built, then that report's sheet is either omitted or included with a clear "unavailable / <reason>" note (documented choice) — the export still succeeds for the available reports.
4. Given the combined export, when triggered, then it gathers each report via the existing `src/api/` fetchers (AD-5); no new backend endpoint if generation is client-side.
5. Given the export control, when no reports are available at all, then it is disabled/hidden.

## Tasks / Subtasks

- [ ] Task 1 — Combined workbook (AC: #1, #2, #3, #4)
  - [ ] On the Overview tab, add "Export all to Excel"; fetch the three reports (reuse `getVersions`/`getVulnerabilities`/`getLicenses`) and build one workbook with a sheet per report via the shared helper (Story 8.12)
  - [ ] Handle a failed/missing report per AC #3 (omit or annotate the sheet)
- [ ] Task 2 — Tests
  - [ ] Frontend: workbook has the expected three sheets from sample reports; a failed report is handled per AC #3; control disabled when nothing is available
  - [ ] `pixi run ci` exits 0

## Dev Notes

Depends on the shared export helper and per-report column specs from 8.12–8.14 — reuse them so a sheet in the combined workbook is byte-for-byte the same shape as the standalone per-tab file. If generation is client-side (recommended in 8.12), the Overview export fetches the three report JSONs and composes sheets; no backend work. [Source: 8-12-export-version-currency-to-excel.md]

The Overview tab currently reads `summary_stats` only; the combined export must fetch the **full** per-report JSONs (not the summary) to fill the sheets. [Source: frontend/src/components/OverviewTab.tsx]

### References

- [Source: _bmad-output/implementation-artifacts/8-12-export-version-currency-to-excel.md, 8-13-…, 8-14-…]
- [Source: frontend/src/components/OverviewTab.tsx, frontend/src/api/reports.ts]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

### Completion Notes List

- **OverviewTab** gains an "Export all to Excel" button (next to the SBOM download). On click it fetches the three full reports via the existing `getVersions`/`getVulnerabilities`/`getLicenses` (AD-5) with `Promise.allSettled`, composes one sheet per fulfilled report using the **existing** `versionCurrencySheet`/`vulnerabilitiesSheet`/`licensesSheet` builders (8.12–8.14) + the shared `buildWorkbook`/`downloadWorkbook` helper (8.12), and downloads `sbom-report.xlsx`. So each sheet is byte-for-byte identical to its standalone per-tab file (AC #2). No backend change, no new dependency.
- **Failed report (AC #3):** a rejected fetch is simply **omitted** from the workbook (documented choice); the export still succeeds for the available reports.
- **AC #5:** the button is hidden when no report is available (derived from `summary_stats.reports` — none present/all failed). A short `exporting` state disables the button while the reports load.
- **Sheet order:** Version Currency → Vulnerabilities → Licenses.
- **Tests:** all three reports → one workbook with the three sheets in order; a failed report is omitted and the rest still export; the control is hidden when no report is available.
- Gate: `pixi run ci` exits 0 — backend 262, frontend 74 (14 files).

### File List

- frontend/src/components/OverviewTab.tsx (Export-all button + combined-workbook handler)
- frontend/src/components/OverviewTab.test.tsx (export tests)
