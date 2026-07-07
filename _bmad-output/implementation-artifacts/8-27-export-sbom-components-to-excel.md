# Story 8.27: Include the SBOM Component Table in the Excel Export

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Reopened (export) of Epic 8.** The Overview "Export all to Excel" (Story 8.15) bundles Version
> Currency, Vulnerabilities, and Licenses — but **not the SBOM itself**, the core artifact of the app.
> This story adds the SBOM **component table** to Excel: a standalone per-tab export on the SBOM tab
> (parity with 8.12–8.14) **and** a sheet in the combined workbook (parity with 8.15). `reportSheets.ts`
> stays the single source both the tab and "export all" use.
>
> **Raw view is EXPLICITLY EXCLUDED from Excel** (see Dev Notes) — JSON/XML is not spreadsheet-shaped, and
> the raw document is already downloadable from the SBOM tab as the native CycloneDX/SPDX file, so nothing
> is lost. Documented here so it is not re-litigated later.
>
> **Pairs with (not blocked by) Story 8.26.** 8.26 adds ecosystem/purl to the normalized component. If those
> fields are present, the sheet includes an ecosystem column; if not, the sheet simply mirrors whatever the
> Components table shows. The two stories are independent and can land in either order.

## Story

As a user,
I want the SBOM component table exported to Excel — on its own from the SBOM tab and inside the combined
"Export all" workbook,
so that the core SBOM artifact is analyzable in a spreadsheet alongside the other three reports, instead of
being the one report missing from Excel.

## Acceptance Criteria

1. **A `sbomComponentsSheet(doc)` builder that mirrors the SBOM tab Components columns.**
   Given a loaded `SbomDocument`, when `sbomComponentsSheet(doc)` is called, then it returns a `SheetSpec`
   named **"SBOM Components"** whose columns mirror the SBOM tab's Components view — **Name, Version, Type,
   License, Relationship** — with one row per `doc.components` entry (name/version/type/license/relationship,
   null → `''`). Where the normalized component carries **ecosystem** and/or **purl** (Story 8.26), include an
   **Ecosystem** column (and a **PURL** column if present); if those fields are absent, omit those columns so
   the sheet always mirrors whatever the Components table currently shows.

2. **A standalone "Export to Excel" button on the SBOM tab (Components view).**
   Given the SBOM tab in the **Components** view with a loaded document, when I click "Export to Excel", then
   a single-sheet `.xlsx` downloads (e.g. `sbom-components.xlsx`) built via `sbomComponentsSheet(doc)` +
   the shared `buildWorkbook`/`downloadWorkbook` helper (`excelExport.ts`) — no new export mechanism.

3. **The combined "Export all to Excel" workbook now includes the SBOM components sheet.**
   Given the Overview tab, when I click "Export all to Excel", then the workbook contains the SBOM Components
   sheet **alongside** Version Currency, Vulnerabilities, and Licenses. The SBOM is the core artifact, so its
   sheet is placed **first** (order: SBOM Components → Version Currency → Vulnerabilities → Licenses). As with
   8.15, a report whose fetch fails is omitted and the export still succeeds for the rest.

4. **The Raw view is NOT exported to Excel (documented exclusion).**
   Given the SBOM tab **Raw** view, when it is shown, then it exposes **no** Excel export — the raw
   CycloneDX/SPDX document is not spreadsheet-shaped and is already downloadable as the native file from the
   Overview "Download SBOM" control and (per 8.6) the tab. Only the Components view exports to Excel.

5. **Tested.**
   A `reportSheets` test for `sbomComponentsSheet` (columns/rows mirror the Components view; ecosystem/purl
   column present when the field exists, absent when it does not; null → `''`); an `SbomTab` test that the
   Components view's "Export to Excel" button triggers `downloadWorkbook` with `sbom-components.xlsx` and that
   the Raw view shows no export button; and the **updated** Overview export-all sheet-name assertion now
   expecting the SBOM sheet in the four-sheet set (SBOM first).

6. **`pixi run ci` green.**

## Tasks / Subtasks

- [ ] **Task 1 — `sbomComponentsSheet(doc)` builder (AC: #1)**
  - [ ] In `frontend/src/reportSheets.ts`, add `sbomComponentsSheet(doc: SbomDocument): SheetSpec` next to
    `versionCurrencySheet`/`vulnerabilitiesSheet`/`licensesSheet`. Import `SbomDocument`/`SbomComponent`
    from `./api/sbom`. Name the sheet `'SBOM Components'` (≤ 31 chars). Columns mirror the tab
    (`SbomTab.tsx:141-144`): `name`→Name, `version`→Version, `type`→Type, `license`→License,
    `relationship`→Relationship. Map each `doc.components` entry, normalizing null → `''` (mirror the
    existing builders' `?? ''`).
  - [ ] **Ecosystem/purl (pairs with 8.26):** if `doc.components` carry an `ecosystem` field, add an
    `ecosystem`→Ecosystem column; if they carry `purl`, add a `purl`→PURL column. Guard so the columns/keys
    are only emitted when the field is present on the type/data, so the sheet mirrors whatever the Components
    table shows and the story stays independent of 8.26's landing.

- [ ] **Task 2 — Standalone SBOM-tab export button (AC: #2, #4)**
  - [ ] In `frontend/src/components/SbomTab.tsx`, add an "Export to Excel" button in the **Components** view
    only (`view === 'components'`). Wire it to build `buildWorkbook([sbomComponentsSheet(doc)])` and
    `downloadWorkbook(wb, 'sbom-components.xlsx')` (import from `../excelExport` and `../reportSheets`).
    Place it near the view toggle / header row (mirror the per-tab export placement in `VersionsTab.tsx`).
    Do **not** render an export control in the **Raw** view.

- [ ] **Task 3 — Add the SBOM sheet to the combined workbook (AC: #3)**
  - [ ] In `frontend/src/components/OverviewTab.tsx::exportAll` (`~L73-89`), fetch the SBOM document
    (`getSbomDocument(status.task_id)` from `../api/sbom`) alongside the three reports in the
    `Promise.allSettled` set, and — when fulfilled — push `sbomComponentsSheet(doc)` **first** into the
    `SheetSpec[]` (order: SBOM Components → Version Currency → Vulnerabilities → Licenses). A rejected SBOM
    fetch is omitted like the others (AC #3 / 8.15 precedent). Keep the "any report available" / disabled
    logic consistent (a document being present is sufficient to enable the export even if the SBOM is the
    only fulfilled source).

- [ ] **Task 4 — Tests (AC: #5)**
  - [ ] `frontend/src/reportSheets.test.ts`: `sbomComponentsSheet` produces the `'SBOM Components'` sheet
    with the mirrored columns and one row per component (null → `''`); when components carry `ecosystem`
    (and/or `purl`), the Ecosystem/PURL column is present; when absent, it is omitted.
  - [ ] `frontend/src/components/SbomTab.test.tsx`: the Components view renders "Export to Excel" and clicking
    it calls `downloadWorkbook` with `sbom-components.xlsx`; the Raw view renders **no** export button.
  - [ ] `frontend/src/components/OverviewTab.test.tsx`: **update** the export-all sheet-name assertion
    (currently `['Version Currency','Vulnerabilities','Licenses']`, `OverviewTab.test.tsx:102`, and the
    partial-failure case at `:114`) to include the SBOM sheet in the expected order (SBOM first). Add a
    `getSbomDocument` mock to the `../api/sbom` mock so the fetch resolves in the test.
  - [ ] `pixi run ci` green.

## Dev Notes

### Why this story exists (the gap)

Story 8.15 composes the Overview "Export all to Excel" workbook from Version Currency, Vulnerabilities, and
Licenses — but the **SBOM component table, the core artifact of the whole app, is absent from Excel**. There is
also no standalone SBOM-tab export, breaking parity with the per-tab exports (8.12–8.14). This story closes both
gaps by adding a single `sbomComponentsSheet(doc)` builder that the SBOM tab and the combined workbook both use.

### Raw view exclusion (decision — do not re-litigate)

The SBOM tab's **Raw** view (`SbomTab.tsx:161-177`, rendering `doc.raw`) is **deliberately not exported to
Excel**:
- The raw document is JSON or XML — a tree/text structure, not a rectangular table — so forcing it into a
  spreadsheet would be lossy and meaningless.
- The native CycloneDX/SPDX document is already downloadable as-is: from the Overview "Download SBOM" control
  (`OverviewTab.tsx`, `status.result_url`) and per Story 8.6's tab. Nothing is lost by excluding it from Excel.
- Therefore only the **Components** view gets an Excel export. If a future need arises to ship the raw bytes,
  that is the existing native-file download, not an `.xlsx`.

### Single source of truth (mirror 8.12–8.15)

`reportSheets.ts` holds one builder per report so the standalone per-tab file and the combined-workbook sheet
are byte-for-byte identical (the 8.12 pattern). `sbomComponentsSheet(doc)` follows the same shape:
`buildWorkbook`/`downloadWorkbook` (`excelExport.ts`) are reused unchanged — no new export mechanism, no new
dependency. Cells may be a `HyperlinkCell` marker if a future column links out (e.g. registry links à la
`versionCurrencySheet`), but the base sheet is plain text mirroring the tab.

### Sheet order (SBOM first)

Per 8.15, the "export all" sheet order is independent of the tab array (see the Story 6.4 note,
`epics.md:1722`). Because the SBOM is the core deliverable, place its sheet **first**:
`SBOM Components → Version Currency → Vulnerabilities → Licenses`. This changes the existing sheet-name
assertion, which must be updated (AC #5).

### Pairs with Story 8.26 (independent)

8.26 adds `ecosystem` (and a correct `purl`) to the normalized `SbomComponent` and, optionally, an ecosystem
column to the SBOM tab. This story's builder mirrors **whatever the Components table shows**: emit the Ecosystem
(and PURL) column only when the field is present on the data/type. If 8.26 has not landed, the guarded columns
are simply omitted — no coupling. If it has, the sheet gains the column automatically. Order of landing does
not matter.

### Current state (anchors — confirm against code; lines may shift)

- **Shared export:** `frontend/src/excelExport.ts` — `SheetSpec` (`:27-31`), `buildWorkbook` (`:42-62`),
  `downloadWorkbook` (`:65-76`); cells support `{text, hyperlink}` and `{text, redText}` markers.
- **Sheet builders:** `frontend/src/reportSheets.ts` — `versionCurrencySheet`/`vulnerabilitiesSheet`/
  `licensesSheet`. Add `sbomComponentsSheet(doc)` here.
- **SBOM tab:** `frontend/src/components/SbomTab.tsx` — Components view renders `doc.components`
  (Name/Version/Type/License/Relationship, `:141-156`); Raw view renders `doc.raw` (`:161-177`);
  `View = 'components' | 'raw'` (`:22`). Add the standalone Export button to the Components view only.
- **SBOM types:** `frontend/src/api/sbom.ts` — `SbomComponent` (name/version/type/purl/license/relationship,
  `:6-13`), `SbomDocument` (`:28-33`), `getSbomDocument(taskId)` (`:35-37`).
- **Combined workbook:** `frontend/src/components/OverviewTab.tsx::exportAll` (`~:73-89`) — assembles the
  `SheetSpec[]` into `sbom-report.xlsx`. Add the SBOM sheet (first).
- **Assertion to update:** `frontend/src/components/OverviewTab.test.tsx:102,114` —
  `['Version Currency','Vulnerabilities','Licenses']` (referenced in the Story 6.4 work).

### Testing standards

Vitest. `reportSheets.test.ts` asserts the returned `SheetSpec` shape (name, columns, rows) directly — no
workbook build needed (mirror the existing builder tests). `SbomTab.test.tsx` mocks `getSbomDocument` and
`downloadWorkbook` and asserts the button-triggered call + Raw-view absence. `OverviewTab.test.tsx` mocks
`getSbomDocument` on the `../api/sbom` mock and reads the last `buildWorkbook` call's sheet names
(`sheetNames()` helper, `OverviewTab.test.tsx:21`).

### Project Structure Notes

- Frontend-only. New builder in `reportSheets.ts`; button in `SbomTab.tsx`; one line in `OverviewTab.tsx`.
  No backend, no new dependency, no `docs/**` change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.27: Include the SBOM Component Table in the Excel Export]
- Shared export: `frontend/src/excelExport.ts:27-76`, builders `frontend/src/reportSheets.ts:11-94`
- SBOM tab: `frontend/src/components/SbomTab.tsx:22,141-177`; types `frontend/src/api/sbom.ts:6-37`
- Combined workbook: `frontend/src/components/OverviewTab.tsx:73-89`
- Assertion to update: `frontend/src/components/OverviewTab.test.tsx:102,114`
- Precedent (per-tab + shared mechanism): `8-12-export-version-currency-to-excel.md`
- Precedent (combined workbook): `8-15-overview-export-all-to-excel.md`
- Pairs with: `8-26-ecosystem-field-in-sbom-document.md` (ecosystem/purl column)

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Claude Opus 4.8, 1M context)

### Debug Log References

None.

### Completion Notes List

- `reportSheets.ts`: added `sbomComponentsSheet(doc)` producing the `'SBOM Components'` sheet with
  Name/Version/Type/License/Relationship, and guarded Ecosystem / PURL columns emitted only when a
  component carries the field (present now that 8.26 landed; independent otherwise). Null → `''`.
- `SbomTab.tsx`: added an "Export to Excel" button in the Components view only (via
  `buildWorkbook([sbomComponentsSheet(doc)])` + `downloadWorkbook(..., 'sbom-components.xlsx')`);
  the Raw view has no export control (documented exclusion).
- `OverviewTab.tsx::exportAll`: fetches `getSbomDocument` alongside the three reports in the
  `Promise.allSettled` set and pushes the SBOM sheet FIRST (order: SBOM Components → Version Currency →
  Vulnerabilities → Licenses); a rejected SBOM fetch is omitted like the others.
- Tests: `reportSheets.test.ts` (sheet columns/rows incl. ecosystem/purl present + absent cases);
  `SbomTab.test.tsx` (Export button click → `sbom-components.xlsx`; Raw view shows no export);
  `OverviewTab.test.tsx` (added `getSbomDocument` mock; updated both sheet-name assertions to expect the
  SBOM sheet first).

### File List

- frontend/src/reportSheets.ts
- frontend/src/reportSheets.test.ts
- frontend/src/components/SbomTab.tsx
- frontend/src/components/SbomTab.test.tsx
- frontend/src/components/OverviewTab.tsx
- frontend/src/components/OverviewTab.test.tsx
