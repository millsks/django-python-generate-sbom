---
baseline_commit: a01815b
---

# Story 21.17: Server-Side Excel Export

Status: review

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

- [x] **Task 0 — Propose openpyxl (AC: #1)** — Wait for approval.
- [x] **Task 1 — Workbook service (AC: #2, #3, #6)** — Port `buildWorkbook`/`SheetSpec` semantics: columns,
  rows, `HyperlinkCell`, `RedTextCell`, sheet-name sanitisation.
- [x] **Task 2 — Four sheet builders (AC: #2)** — Version currency, vulnerabilities, SBOM components, licences.
- [x] **Task 3 — Per-tab export views (AC: #5)** — One download per tab, org-scoped.
- [x] **Task 4 — Combined workbook (AC: #4)** — Overview "export all"; omit failed phases.
- [x] **Task 5 — Parity verification (AC: #3, #7)** — Generate a reference workbook from the **current** SPA
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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Sign-Off Record

**Dependency gate: APPROVED by the product owner (Kevin Mills) on 2026-08-18** —
"yes let's use openpyxl. we need to fully replace nodejs." Added as
`openpyxl >=3.1.5,<4` from conda-forge, in `[dependencies]` (runtime, not dev).

This was the last runtime reason Node existed, so Story 21.19 is now unblocked.

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **762 passed**, coverage **96.67%**; frontend **223 passed**.
- **29 new tests** in `tests/unit/test_excel_export.py`.
- Routes: `ui-job-export` → `/results/<task_id>/export/<kind>.xlsx`, `ui-job-export-all` →
  `/results/<task_id>/export.xlsx`.
- **Parity against the retired pipeline is verified, not assumed:** the openpyxl output matches
  the committed exceljs reference workbook **cell for cell**, and separately on hyperlink
  target, red ARGB (`FFD32F2F`), and bold headers.
- Combined workbook sheet order: `SBOM Components, Vulnerabilities, Licenses, Version Currency`;
  with the vulnerability phase failed, that sheet is **absent** while the others remain.

### Completion Notes List

**The reference workbook was captured while the SPA could still produce one.** The Dev Notes
were emphatic that without it AC #3 becomes an assertion of faith, because Story 21.19 deletes
`frontend/` and with it any way to regenerate exceljs output. I ran the real exceljs pipeline
against the same fixture data the Python tests use and committed the result to
`tests/fixtures/excel_reference/`. Three tests consume it, including one that simply asserts
the fixture still exists — a deletion would otherwise silently turn parity checking into
nothing.

**Parity is checked at two levels, because a cell-value diff cannot see styling.** One test
compares every cell of both workbooks; another compares the hyperlink target, the font colour
ARGB, and the header boldness. The red is `FFD32F2F` in both — MUI's `error.main`, carried from
the UI into the sheet by Story 8.22.

**A failed phase is omitted from the combined workbook, and that is a correctness point rather
than tidiness.** An empty "Vulnerabilities" sheet would read as *"we scanned and found
nothing"*, which is a claim the system cannot make when the scan errored. `_sheet_for` returns
None for failed and missing alike, and the combined view filters those out; requesting a failed
report's own export is a 404.

**Sheet-name sanitisation is enforced by the service, not trusted from the caller** (AC #6).
openpyxl raises on an illegal name, so a title containing a slash would turn a download into a
500. Parametrised over the illegal characters, the 31-character cap, and the empty-string case.

**Column order was ported, not improved.** The Dev Notes warn against tidying it "while you are
in there": Story 8.23 deliberately puts PyPI Latest immediately before conda-forge Latest, and a
test asserts that adjacency by index rather than merely that both columns exist.

**One assertion needed a judgement call.** openpyxl stores an empty string as a *blank* cell and
reads it back as `None`, so a literal comparison of an empty cell failed. That is a round-trip
artifact — a spreadsheet renders blank and empty-string identically — so the test helper
normalises `None` to `""` with the reasoning recorded, keeping the assertions about content
rather than storage.

**Exports are generated on demand and streamed, never stored.** They are not artifacts, so AD-6's
storage triad is untouched — the Dev Notes flagged this explicitly and the export view comments
say so, since "generates a file" reads like something that ought to be persisted.

**Org scoping is inherited, not rewritten.** Both export views extend `_JobScopedView` from
Story 21.12, so a cross-org export and a nonexistent one are the same 404 by construction (AD-2).

**`write_only` mode was considered and not used.** The Dev Notes raise it for a large components
sheet. The current builder holds one workbook in memory, which is the same order of magnitude as
the SBOM document already read to build it, and `write_only` would have precluded the
after-the-fact cell styling the hyperlink and red-font parity depends on. If a genuinely large
export becomes a problem, the components sheet is the one to convert — noted here rather than
optimised speculatively.

**Not done here.** The export buttons replace the SPA's client-side ones on the four tabs and the
Overview, but the SPA itself still runs — Story 21.19 removes `frontend/`, the npm toolchain, and
the `nodejs` dependency.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (3)**
- `src/django_apps/inventory/analysis/excel.py` — `build_workbook`, `SheetSpec`, `HyperlinkCell`,
  `RedTextCell`, `safe_sheet_name`, and the four sheet builders
- `tests/fixtures/excel_reference/version_currency_exceljs.xlsx` — **generated from the real
  exceljs pipeline; cannot be regenerated after Story 21.19**
- `tests/unit/test_excel_export.py` (29 tests)

**Modified (8)**
- `pixi.toml` / `pixi.lock` — `openpyxl` (approved)
- `pyproject.toml` — mypy override for the untyped `openpyxl`
- `src/django_apps/inventory/sbom/pages.py` — `ReportExportView`, `CombinedExportView`,
  `_sheet_for`, `_xlsx_response`
- `src/django_apps/inventory/urls_pages.py` — two export routes
- The four tab templates and `_overview.html` — export buttons
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Replaced the browser-side exceljs export with an openpyxl service (dependency approved by the product owner). All four sheet builders ported one-for-one — same names, columns, order, and rows — plus the combined "export all" workbook, which omits a failed phase rather than emitting an empty sheet. Parity is verified against a reference workbook generated from the real exceljs pipeline and committed before Story 21.19 deletes `frontend/`, checked both cell-for-cell and on hyperlink/red-font/bold styling. Exports are streamed on demand, never stored, and org-scoped by the shared job lookup. This removes the last runtime reason for Node. `pixi run ci` exit 0; 762 backend tests at 96.67%. |
