# Story 8.23: Version Currency — Side-by-Side PyPI / conda-forge Latest Columns

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user reading the version currency report,
I want the "PyPI Latest" and "conda-forge Latest" columns to sit next to each other,
so that I can compare the two latest versions at a glance without scanning across the
other columns.

## Acceptance Criteria

1. **Adjacent latest columns, renamed.** In the version currency **table**, the existing
   "Latest" column is moved to sit immediately **left** of the "conda-forge Latest"
   column and its header is renamed from **"Latest"** to **"PyPI Latest"**, so the two
   latest-version columns are adjacent in the order **PyPI Latest | conda-forge Latest**.
2. **Verified source label.** The renamed column genuinely shows the **PyPI** latest
   (`VersionEntry.latest`, `api/reports.ts:56`) — confirmed accurate, so "PyPI Latest"
   is the correct label (not a guess).
3. **Exports match the table.** The version-currency Excel export and the Overview
   "export all" workbook use the **same** column order and the **"PyPI Latest"** header,
   so UI and exports agree.
4. **Sort + red-font behavior preserved.** The default sort (Story 8.16) still targets
   its intended column after the reorder, and Story 8.22's conditional red font on the
   conda-forge-latest cells is unaffected by the reordering.
5. **Tested.** Tests assert the tab renders "PyPI Latest" immediately before
   "conda-forge Latest", and the export sheet has the columns in that order with the new
   label.

## Tasks / Subtasks

- [ ] **Task 1 — Reorder + rename in the table (AC: #1, #2, #4)**
  - [ ] In `frontend/src/components/VersionsTab.tsx`, the sortable `COLUMNS` array lists
    `name, installed, latest, currency` (`VersionsTab.tsx:31-36`) and the header row then appends the
    **non-sortable** `conda-forge Latest`, `LTS`, `Source` cells (`VersionsTab.tsx:159-161`); the body
    renders `installed`, `latest`, `currency` (Status), then `CondaLatestCell`, `LtsCell`, `SourceCell`
    (`VersionsTab.tsx:173-186`). Rework so the **latest** column renders immediately before
    **conda-forge Latest**: place "PyPI Latest" and "conda-forge Latest" adjacently in both the header
    and the body. Rename the `latest` column label from `'Latest'` to `'PyPI Latest'` (`VersionsTab.tsx:34`).
  - [ ] Keep `latest` **sortable** if it stays in `COLUMNS` (preferred — retains its `TableSortLabel`);
    if the reorder is easier by rendering it outside `COLUMNS`, ensure it still sorts (do not silently
    drop the sort affordance). The target order is: Package | Installed | Status | **PyPI Latest** |
    **conda-forge Latest** | LTS | Source — or Package | Installed | **PyPI Latest** | **conda-forge
    Latest** | Status | LTS | Source. Pick the layout that keeps the two latest columns adjacent and
    the sortable columns' `TableSortLabel` intact; record the chosen order in the Dev Agent Record.
- [ ] **Task 2 — Match the Excel export (AC: #3)**
  - [ ] In `frontend/src/reportSheets.ts`, `versionCurrencySheet` columns are
    `name, installed, latest (header "Latest (PyPI)"), conda_latest (header "conda-forge Latest"),
    currency, lts, on_lts, ecosystem` (`reportSheets.ts:14-23`). Reorder so `latest` sits immediately
    before `conda_latest`, and change the `latest` header to **"PyPI Latest"** (from "Latest (PyPI)")
    to match the table label exactly. The Overview "export all" workbook (Story 8.15) reuses
    `versionCurrencySheet`, so it inherits the change — no separate edit.
- [ ] **Task 3 — Preserve sort + 8.22 red font (AC: #4)**
  - [ ] Confirm the default sort (`orderBy` initial value, `VersionsTab.tsx:97` — currently `'name'`
    per Story 8.16) still points at the intended column after the reorder; the reorder is visual only,
    so `CURRENCY_RANK`/`compare` (`VersionsTab.tsx:28,88-91`) need no change. Verify Story 8.22's
    `CondaLatestCell` red font (`mismatch={row.latest_mismatch}`) and the export's red-text marker still
    apply to the conda-forge cell in its new position (they key off the value, not the column index).
- [ ] **Task 4 — Tests (AC: #5)**
  - [ ] `frontend/src/components/VersionsTab.test.tsx`: assert the header "PyPI Latest" renders
    immediately before "conda-forge Latest" (e.g. via column-order inspection of the header cells).
  - [ ] `frontend/src/reportSheets.test.ts`: update `versionCurrencySheet` expectations so the columns
    array has `latest` immediately before `conda_latest` with header "PyPI Latest" (adjust the existing
    header-list assertion, `reportSheets.test.ts:12-23`).

## Dev Notes

### Source verification (AC #2) — done

The current "Latest" column **is** the PyPI latest: `VersionEntry.latest` is the PyPI latest
version (`api/reports.ts:56`), and `latest_mismatch` is documented as "true when the **PyPI**
latest and conda-forge latest diverge" (`api/reports.ts:62`). The export already half-acknowledges
this with the header **"Latest (PyPI)"** (`reportSheets.ts:18`). So renaming the table header to
**"PyPI Latest"** is accurate — no relabeling to a different source is needed.

### Current layout

- **Table:** sortable `COLUMNS = [name, installed, latest ('Latest'), currency ('Status')]`
  (`VersionsTab.tsx:31-36`); the header then appends non-sortable `conda-forge Latest`, `LTS`,
  `Source` (`VersionsTab.tsx:159-161`); the body renders name, installed, latest, Status chip, then
  `CondaLatestCell`, `LtsCell`, `SourceCell` (`VersionsTab.tsx:170-186`). So today "Latest" and
  "conda-forge Latest" are separated by the Status column.
- **Export:** `versionCurrencySheet` columns place `latest` then `conda_latest` **already adjacent**
  in the sheet (`reportSheets.ts:14-23`) but with header "Latest (PyPI)"; this story only renames that
  header to "PyPI Latest" for consistency (the order is already correct there).

### Interaction with Story 8.22 (red font)

Story 8.22 adds a conditional **red font** to the conda-forge-latest cell when `latest_mismatch` is
true, in both the table (`CondaLatestCell`) and the export (a red-text marker cell). Both key off the
cell **value / the `latest_mismatch` flag**, not the column position, so moving the column does not
affect 8.22. If 8.22 and 8.23 land in either order, neither breaks the other; just re-verify the red
cell after the reorder.

### Default sort (Story 8.16)

The default `orderBy` is `'name'` (`VersionsTab.tsx:97`) and sorting is value-based via `compare`
(`VersionsTab.tsx:88-91`), independent of column display order. The reorder is purely presentational,
so default-sort behavior is unchanged — just confirm the `latest` column keeps its `TableSortLabel`
if it remains in `COLUMNS`.

### Cross-story dependencies

- **Story 8.10** — defines the conda-forge latest + `latest_mismatch` divergence this compares against.
- **Story 8.12 / 8.15** — the version-currency export and Overview "export all" workbook that must match
  the new order/label (both via `versionCurrencySheet`).
- **Story 8.16** — default per-tab sort; confirm unaffected.
- **Story 8.22** — conda-forge-latest red font; independent of the reorder (verify, don't change).

### Testing standards

- Vitest + RTL, `frontend/src/components/VersionsTab.test.tsx` and `frontend/src/reportSheets.test.ts`.
  Assert header/column order rather than internal state. No MSW.

### Project Structure Notes

- Frontend-only: `frontend/src/components/VersionsTab.tsx`, `frontend/src/reportSheets.ts` (+ their
  tests). `frontend/src/api/reports.ts` is referenced for field semantics only — no change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.23: Version Currency — Side-by-Side PyPI / conda-forge Latest Columns]
- Table: `frontend/src/components/VersionsTab.tsx:31-36` (`COLUMNS`), `:159-161` (header), `:170-186` (body), `:97` (default sort)
- Export: `frontend/src/reportSheets.ts:14-23` (`versionCurrencySheet` columns)
- Field semantics: `frontend/src/api/reports.ts:56,62`
- Related stories: `8-10-conda-forge-latest-and-divergence.md`, `8-12-export-version-currency-to-excel.md`, `8-15-overview-export-all-to-excel.md`, `8-16-default-sort-order-per-tab.md`, `8-22-version-currency-excel-conda-forge-color.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
