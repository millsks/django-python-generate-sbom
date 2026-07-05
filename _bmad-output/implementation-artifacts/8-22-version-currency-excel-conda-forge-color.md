# Story 8.22: Version-Currency Excel Export Carries the conda-forge-Latest Text Color

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user exporting the version currency report to Excel,
I want the "conda-forge Latest" cell to be red when it diverges from the PyPI latest,
so that mismatches stay identifiable in the spreadsheet exactly as they are in the UI.

## Acceptance Criteria

1. **Red text on mismatch, in the export.** In the exported version-currency `.xlsx`,
   a "conda-forge Latest" cell whose value **diverges** from the PyPI latest is
   rendered with a **red font**, mirroring the UI's red text in the Version Currency
   tab.
2. **Same condition as the UI.** The red-font rule uses the **same** mismatch
   condition the UI uses — `latest_mismatch === true` on the version entry — so the
   export and the on-screen table always agree on which cells are flagged.
3. **Non-mismatch cells unchanged.** Cells with no mismatch (and empty/absent
   conda-forge values) keep the normal (default) font — only diverging cells turn red.
4. **Tested.** A test asserts that a mismatched conda-forge-latest cell in the
   generated sheet has the red font, and a non-mismatched cell does not.

## Tasks / Subtasks

- [ ] **Task 1 — Carry the mismatch flag into the sheet spec (AC: #1, #2, #3)**
  - [ ] In `frontend/src/reportSheets.ts`, `versionCurrencySheet` currently emits
    `conda_latest: pkg.conda_latest ?? ''` as plain text (`reportSheets.ts:30`). Mark that cell so
    the workbook builder can style it red when `pkg.latest_mismatch === true` — mirror the existing
    `HyperlinkCell` pattern (a cell value can be a marker object the builder recognizes). Introduce a
    small styled-text marker (e.g. `RedTextCell { text: string; redText: true }`) in
    `frontend/src/excelExport.ts` next to `HyperlinkCell` (`excelExport.ts:11-15`), and in
    `versionCurrencySheet` emit `conda_latest: pkg.latest_mismatch && pkg.conda_latest ? { text: pkg.conda_latest, redText: true } : (pkg.conda_latest ?? '')`.
    Do **not** color empty/absent conda values (AC #3).
- [ ] **Task 2 — Apply the red font in the workbook builder (AC: #1, #3)**
  - [ ] In `frontend/src/excelExport.ts`, `buildWorkbook` already special-cases hyperlink cells in
    `added.eachCell` (`excelExport.ts:37-39`). Add a sibling check: if the cell value is the red-text
    marker, set `cell.value = value.text` and `cell.font = { color: { argb: 'FFD32F2F' } }` (a red ARGB;
    align to the theme's `error` red, e.g. MUI `error.main` ~ `#D32F2F`). Add a type guard
    `isRedText(value)` mirroring `isHyperlink` (`excelExport.ts:23-25`).
- [ ] **Task 3 — Confirm the UI condition matches (AC: #2)**
  - [ ] Verify the UI rule so the export uses the identical condition: `VersionsTab.tsx`'s
    `CondaLatestCell` renders red (`color="error"`) when `mismatch` is true, and it is passed
    `mismatch={row.latest_mismatch}` (`VersionsTab.tsx:77-86,179`). Use `latest_mismatch` — not a
    recomputed string comparison — so the two stay in lockstep.
- [ ] **Task 4 — Tests (AC: #4)**
  - [ ] `frontend/src/reportSheets.test.ts`: extend `versionCurrencySheet` coverage so a package with
    `latest_mismatch: true` emits the red-text marker for `conda_latest`, and one without it emits plain
    text (mirror the existing hyperlink-cell assertions, `reportSheets.test.ts:5-38`).
  - [ ] `frontend/src/excelExport.test.ts`: add a case that `buildWorkbook` renders the red-text marker
    as a cell with `cell.font.color.argb` set to the red ARGB and the plain text value (mirror the
    existing hyperlink-cell test, `excelExport.test.ts:29-40`).

## Dev Notes

### Why this story exists (the gap)

The Version Currency tab renders the "conda-forge latest" text in **red** when it diverges
from the PyPI latest (Story 8.10) to flag that conda-forge is out of step. The Excel export
(Story 8.12) copies the value as plain text and loses that signal, so mismatches are no longer
visually identifiable in the spreadsheet. This story carries the same conditional red font
into the exported sheet.

### Current state

- **UI (source of truth for the rule):** `CondaLatestCell`
  ```tsx
  return mismatch ? (
    <Typography component="span" variant="body2" color="error" ...>{condaLatest}</Typography>
  ) : (<>{condaLatest}</>)
  ```
  passed `mismatch={row.latest_mismatch}` (`VersionsTab.tsx:77-86`, `:179`). `latest_mismatch` is
  `true` when the PyPI latest and conda-forge latest diverge (`api/reports.ts:62`).
- **Export (needs the change):** `versionCurrencySheet` emits `conda_latest: pkg.conda_latest ?? ''`
  with no styling (`reportSheets.ts:30`). `buildWorkbook` only styles hyperlink cells
  (`excelExport.ts:37-39`) — the mechanism to extend.

### Styling mechanism (mirror the hyperlink pattern)

The workbook builder already recognizes a marker cell value (`{ text, hyperlink }`) and applies a
link font. Add a parallel marker for red text and a matching guard, so `versionCurrencySheet` stays
declarative and the styling lives in one place (`buildWorkbook`). Keep the red ARGB a single named
constant; align it to the theme `error` red (`#D32F2F` → `FFD32F2F`).

### Scope guard

Only the **version currency** sheet's conda-forge-latest column is in scope. Do not add coloring to
the vulnerabilities/licenses sheets or other columns. The Overview combined workbook reuses
`versionCurrencySheet`, so it inherits the fix automatically — no separate change there.

### Cross-story dependencies

- **Story 8.10** — defines `latest_mismatch` and the UI red-text divergence rule this mirrors.
- **Story 8.12** — the version-currency Excel export this augments.
- **Story 8.15** — the Overview "export all" workbook reuses `versionCurrencySheet` and inherits the fix.

### Testing standards

- Vitest, `frontend/src/reportSheets.test.ts` and `frontend/src/excelExport.test.ts`. Build a real
  `ExcelJS.Workbook` via `buildWorkbook` and assert on `worksheet.getRow(n).getCell(c).font` (the
  existing excelExport test reads `cell.font?.underline` the same way). No MSW.

### Project Structure Notes

- Frontend-only: `frontend/src/reportSheets.ts`, `frontend/src/excelExport.ts` (+ their tests).
  `frontend/src/components/VersionsTab.tsx` and `frontend/src/api/reports.ts` are referenced for the
  condition only — no change required there.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.22: Version-Currency Excel Export Carries the conda-forge-Latest Text Color]
- Export: `frontend/src/reportSheets.ts:11-38` (`versionCurrencySheet`), `frontend/src/excelExport.ts:23-43` (`buildWorkbook`)
- UI rule: `frontend/src/components/VersionsTab.tsx:77-86,179` (`CondaLatestCell`, `mismatch={row.latest_mismatch}`)
- Field: `frontend/src/api/reports.ts:62` (`latest_mismatch`)
- Related stories: `8-10-conda-forge-latest-and-divergence.md`, `8-12-export-version-currency-to-excel.md`, `8-15-overview-export-all-to-excel.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
