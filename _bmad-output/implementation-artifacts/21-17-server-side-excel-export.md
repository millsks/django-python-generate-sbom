# Story 21.17: Server-Side Excel Export

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.16**, once all four report tabs exist. **This is the last thing standing
> between the project and a Node-free toolchain** — Story 21.19 cannot remove Node until this lands.

> **⚠ SIGN-OFF GATE.** This story proposes **`openpyxl`** as a new runtime dependency (conda-forge first).
> Propose; do not add until explicitly approved (Control Constraints §7).

## Story

As a user,
I want to export reports to Excel,
so that I can share and analyse results outside the application.

## Acceptance Criteria

1. **openpyxl is proposed and added only on approval.**
   Given the project has no server-side spreadsheet library, when the export service is built, then the story
   **proposes** `openpyxl` and adds it only after explicit approval.
2. **All four sheet builders reach output parity.**
   Given `reportSheets.ts` defines four builders — `versionCurrencySheet` (`:12`), `vulnerabilitiesSheet`
   (`:49`), `sbomComponentsSheet` (`:79`), and `licensesSheet` (`:112`) — when they are reimplemented as a
   Django service, then each produces a sheet with the **same name**, the **same columns in the same order**,
   and the **same row content** as the exceljs output.
3. **Hyperlink and red-font styling survive.**
   Given `excelExport.ts` renders `HyperlinkCell` values as clickable links and `RedTextCell` values in
   `RED_ARGB = 'FFD32F2F'` (MUI `error.main`, Story 8.22), when the openpyxl equivalent renders, then
   hyperlinks are clickable in Excel and the conda-forge divergence warning renders in the same red —
   **verified against a reference workbook**, not asserted only on cell values.
4. **The combined workbook works.**
   Given the Overview offers an "export all" workbook (Story 8.15), when it is converted, then a single
   download contains all available sheets, and a report whose phase **failed is omitted** from the workbook
   rather than emitted empty.
5. **Exports are org-scoped.**
   Given exports contain job data, when an export is requested, then it is reachable only by a user entitled
   to that job's results, with cross-org requests indistinguishable from missing ones.
6. **Sheet names stay Excel-legal.**
   Given `SheetSpec` carries the constraint "keep ≤ 31 chars, no `[]:*?/\`", when sheets are named, then the
   service enforces it rather than relying on the caller.
7. **Gate green.**
   When the story completes, then tests cover all four sheets, the combined workbook, the failed-phase
   omission, the styling parity, and cross-org denial, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 0 — Propose openpyxl (AC: #1)** — Wait for approval.
- [ ] **Task 1 — Workbook service (AC: #2, #3, #6)** — Port `buildWorkbook`/`SheetSpec` semantics: columns,
  rows, `HyperlinkCell`, `RedTextCell`, sheet-name sanitisation.
- [ ] **Task 2 — Four sheet builders (AC: #2)** — Version currency, vulnerabilities, SBOM components, licences.
- [ ] **Task 3 — Per-tab export views (AC: #5)** — One download per tab, org-scoped.
- [ ] **Task 4 — Combined workbook (AC: #4)** — Overview "export all"; omit failed phases.
- [ ] **Task 5 — Parity verification (AC: #3, #7)** — Generate a reference workbook from the **current** SPA
  before `frontend/` is deleted, and diff against it.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/excelExport.ts:1-3` header comment — "Builds an .xlsx in the browser from report data already
  fetched — no backend endpoint."
- `RED_ARGB = 'FFD32F2F'` — "Theme error red (MUI error.main #D32F2F) as an exceljs ARGB".
- `HyperlinkCell = { text, hyperlink }`; `RedTextCell = { text, redText: true }`.
- `SheetSpec.name` comment: "keep ≤ 31 chars, no `[]:*?/\`".
- Sheet builders: `reportSheets.ts:12` version currency, `:49` vulnerabilities, `:79` SBOM components,
  `:112` licences.
- Originating stories: 8.12 (version currency), 8.13 (vulnerabilities), 8.14 (licences), 8.15 (Overview export
  all), 8.22 (conda-forge divergence red), 8.23 (PyPI Latest column order), 8.27 (SBOM components).

### Capture the reference workbook before deleting the frontend

Story 21.19 deletes `frontend/`. Once it is gone, there is no way to regenerate the exceljs output to compare
against. **Generate and commit reference workbooks as test fixtures during this story**, while the SPA still
runs. Without them AC #3 is unverifiable and parity becomes an assertion of faith.

### openpyxl covers everything needed

Hyperlinks (`cell.hyperlink`) and font colour (`Font(color="FFD32F2F")`) are both first-class in openpyxl, so
parity is achievable. The work is in porting the row/column specs faithfully, not in library capability.

### Watch for

- **Streaming vs. in-memory**: a large SBOM components sheet can be big. Consider `write_only` mode for the
  components sheet.
- **`DEFAULT_FILE_STORAGE` is irrelevant here** — exports are generated on demand and streamed, not stored as
  artifacts, so **AD-6** (storage triad) is unaffected.
- **Do not change column order** "while you are in there" — Story 8.23 deliberately places PyPI Latest
  immediately before conda-forge Latest.

### Testing standards

- Golden-file tests: open the generated workbook with openpyxl and assert sheet names, header rows, a sample of
  data rows, at least one hyperlink target, and the red font ARGB.
- A test asserting a failed phase's sheet is absent from the combined workbook.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.17: Server-Side Excel Export]
- `frontend/src/excelExport.ts`, `frontend/src/reportSheets.ts`, and the export buttons in
  `OverviewTab.tsx`, `SbomTab.tsx`, `VulnerabilitiesTab.tsx`, `LicensesTab.tsx`, `VersionsTab.tsx`.
- Upstream: `21-13` … `21-16`. Downstream: `21-19-retire-react-spa-and-node-toolchain.md` (**blocked by this
  story**).

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Sign-Off Record

_(openpyxl dependency gate — record approval here before starting)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
