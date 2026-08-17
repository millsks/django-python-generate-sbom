# Story 21.16: Version Currency Tab

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.15**. The last of the four detail tabs. **The trickiest tab to convert**
> — its status column sorts by a class rank, not alphabetically.

## Story

As a user,
I want to see how far behind my dependencies are,
so that I can prioritise upgrades.

## Acceptance Criteria

1. **All seven columns are converted.**
   Given `VersionsTab.tsx` renders Package, Installed, Status, PyPI Latest, conda-forge Latest, LTS, and
   Source, when it is converted, then the same seven columns render in the same order — note that PyPI Latest
   is deliberately ordered immediately before conda-forge Latest so the two sit side by side (Story 8.23).
2. **Package names link to their registry.**
   Given Story 8.9 links package names to PyPI or prefix.dev's conda-forge explorer, when the table renders,
   then a package with a known ecosystem links to its registry detail page and one with an unknown ecosystem
   renders as plain text.
3. **Status sorts by class rank, not alphabetically.**
   Given `CURRENCY_RANK` (`VersionsTab.tsx:28`) orders `behind-2+` (3) > `behind-1` (2) > `current` (1) >
   `unknown` (0), when sorting moves to the server, then the same rank ordering is preserved — **asserted
   explicitly by a test**, because an alphabetical sort would silently produce `behind-1, behind-2+, current,
   unknown` and look plausible.
4. **The default sort matches today's.**
   Given Story 8.16 set per-tab defaults and `VersionsTab.tsx:100` defaults to `orderBy = 'name'` ascending,
   when the table renders with no explicit sort, then it sorts by package name ascending.
5. **Divergence and LTS states render.**
   Given a conda-forge latest that diverges from the PyPI latest is shown in the warning colour (Story 8.10)
   and the LTS cell distinguishes "On LTS (x.y)", "LTS x.y (target)", and "no LTS tracked" (Story 8.7), when
   the tab is converted, then all of those states still render.
6. **A failed phase shows the shared notice.**
   Given the version phase can fail independently (FR-6.7), when it has failed, then the tab shows the shared
   failure notice from Story 21.14 with its recorded reason.
7. **Gate green.**
   When the story completes, then tests assert the `CURRENCY_RANK` ordering, the default sort, registry links
   for known and unknown ecosystems, divergence flagging, all three LTS states, and the failed-phase notice,
   and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — `VersionTable` (AC: #1, #2, #5)** — Seven columns in order; registry links; divergence and
  LTS cell renderers.
- [ ] **Task 2 — Rank-aware server-side ordering (AC: #3, #4)** — Annotate or order by an explicit rank
  mapping; never lexical on the currency string.
- [ ] **Task 3 — Failure notice reuse (AC: #6)**.
- [ ] **Task 4 — Tests + gate (AC: #7)** — The rank test is the load-bearing one.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/components/VersionsTab.tsx:28` —
  `CURRENCY_RANK = { 'behind-2+': 3, 'behind-1': 2, current: 1, unknown: 0 }`, described as "Descending
  outdatedness: behind-2+ first, then behind-1, current, unknown".
- `:34-39` — sortable `COLUMNS` are name, installed, currency, latest; conda-forge Latest, LTS, and Source are
  rendered as non-sortable columns after them. The comment explains PyPI Latest is "ordered last so it renders
  immediately before the appended conda-forge Latest column" (Story 8.23).
- `:100` — `orderBy` defaults to `'name'`, `order` to `'asc'` (Story 8.16).
- `:41-45` — badges: `current` → "Current"/success; `unknown` → "Unknown"/default; otherwise "Behind 2+" or
  "Behind 1"/warning.
- `:50-57` — `LtsCell`: no LTS → em dash; on LTS → success chip "On LTS (x.y)"; else outlined info chip
  "LTS x.y (target)" (Story 8.7).
- `:80-89` — `CondaLatestCell` renders in the error colour with a "Differs from the PyPI latest" title when
  `latest_mismatch` (Story 8.10).
- `frontend/src/registryLinks.ts` — `registryUrl({name, version, ecosystem})` and `ecosystemLabel(ecosystem)`.
- Excel export is Story 8.12 (plus 8.22's red divergence, 8.23's column order) — reimplemented server-side in
  **Story 21.17**.

### The rank sort is the defect magnet

`sortBy('currency')` in the SPA compares `CURRENCY_RANK[a] - CURRENCY_RANK[b]`. A naive server-side
`order_by('currency')` sorts the *string*, producing an order that looks sorted and is wrong. Implement it as
an explicit rank annotation (a `Case`/`When` or an in-Python key) and assert the resulting sequence in a test.

### Note on the SPA's toggle asymmetry

`sortBy` sets `order` to `'desc'` when switching to a **new** column but toggles when re-clicking the same one
(`:124-130`). Match the observable result: clicking "Status" first shows the most-outdated packages first.

### Testing standards

- A test with one package in each currency class asserting the exact rendered sequence for a Status sort.
- A test asserting `ecosystem: null` renders plain text with no anchor.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.16: Version Currency Tab]
- `frontend/src/components/VersionsTab.tsx`, `frontend/src/registryLinks.ts`, `frontend/src/icons.ts`,
  `generate_sbom/analysis/services/versions.py`.
- Upstream: `21-15-licenses-tab.md`. Downstream: `21-17`.

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
