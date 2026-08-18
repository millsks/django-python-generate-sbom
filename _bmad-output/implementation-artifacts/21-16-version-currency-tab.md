---
baseline_commit: aaba867
---

# Story 21.16: Version Currency Tab

Status: review

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

- [x] **Task 1 — `VersionTable` (AC: #1, #2, #5)** — Seven columns in order; registry links; divergence and
  LTS cell renderers.
- [x] **Task 2 — Rank-aware server-side ordering (AC: #3, #4)** — Annotate or order by an explicit rank
  mapping; never lexical on the currency string.
- [x] **Task 3 — Failure notice reuse (AC: #6)**.
- [x] **Task 4 — Tests + gate (AC: #7)** — The rank test is the load-bearing one.

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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **733 passed**, coverage **96.56%**; frontend **223 passed**.
- **17 new tests** in `tests/unit/test_versions_tab.py`, plus **1 regression test** added back
  into `test_vulnerabilities_tab.py`.
- Rank sort asserted as an exact sequence: `?sort=-currency` yields
  `behind-2+ → behind-1 → current → unknown`, and `?sort=currency` reverses it.
- Header order asserted by **parsing the `<th>` cells** and comparing the list to the seven
  expected labels; adjacency of PyPI Latest and conda-forge Latest asserted by index arithmetic.
- Registry links: PyPI project URL with version, prefix.dev conda-forge URL, and **no anchor**
  for an unknown ecosystem; encoding covered by a unit test on `registry_url` directly.

### Completion Notes List

**The rank sort was the point of the story, and the test is built to fail an alphabetical
implementation.** Alphabetically the classes order `behind-1, behind-2+, current, unknown`; by
rank descending they must be `behind-2+, behind-1, current, unknown`. The two agree on almost
nothing except that `behind-1` precedes `behind-2+`, so the test asserts the **exact rendered
sequence** and separately asserts `behind2pkg` precedes `behind1pkg` — the single comparison
that inverts between the two implementations. The fixture also inserts the four packages in an
order that is neither rank nor alphabetical, so a pass cannot be a coincidence of input order.

**I avoided the trap I hit in Story 21.14.** `Meta.order_by` names a **column**, not an
accessor, so the currency column carries `order_by="currency_rank"` and `Meta.order_by` is
`name` (the Story 8.16 default). Getting this wrong produces no error — the table simply
renders unsorted — which is why both this and 21.14 assert row *sequence* rather than mere
presence.

**A latent crash found here and fixed in Story 21.14's code.** `render_lts` returned
`format_html("—")` for a package with no tracked LTS, and `format_html` raises `TypeError` when
given no arguments. The identical bug was already sitting in `render_advisory_url` from 21.14 —
it had never fired because every vulnerability fixture happened to supply an advisory URL, so a
finding without one would have 500'd. Both now return plain text, and I added
`test_a_finding_with_no_advisory_url_renders_a_dash` to 21.14's module so the older path is
covered rather than merely fixed.

**Two of my own assertions were too brittle and got rewritten, not loosened.** Matching
`">PyPI Latest<"` finds sortable headers (wrapped in an anchor) but misses non-sortable ones
(bare text with surrounding whitespace). The tests now parse the `<th>` cells and compare the
extracted list, which is both robust and a stronger claim — it pins the complete column set and
its order, not just relative positions of a few labels.

**Column order is load-bearing and is asserted as adjacency.** Story 8.23 put PyPI Latest
immediately before conda-forge Latest so the two can be compared at a glance; the test asserts
`index(conda) == index(pypi) + 1` rather than merely that both appear.

**Registry links return None rather than a guess.** An unknown ecosystem renders plain text,
because a fabricated URL would 404 — the same choice `registryLinks.ts` made. Package names are
URL-encoded, with a direct unit test on `registry_url` covering a name containing a space and
one containing a slash, since a package name is data and must not be able to break out of the
URL.

**All three LTS states render distinctly** (none tracked, on it, targeting it), and the test
also asserts the absence of `"On LTS (None)"` — the shape a naive truthiness check would emit.

**The placeholder test is retired, not deleted.** With all four detail tabs real,
`test_no_tab_is_a_placeholder_any_more` now iterates every tab and asserts none says "arrives in
Story" — so a tab regressing to a stub is caught, which simply removing the test would not do.

**Not done here.** The Excel export of this report — including Story 8.22's red divergence and
8.23's column order — is Story 21.17.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (2)**
- `src/django_apps/inventory/templates/inventory/sbom/tabs/_versions.html` — the real tab
- `tests/unit/test_versions_tab.py` (17 tests)

**Modified (4)**
- `src/django_apps/inventory/analysis/tables.py` — `VersionTable`, `version_rows`,
  `CURRENCY_RANK`, `CURRENCY_BADGES`, `registry_url`, `ECOSYSTEM_LABELS`; fixed the bare
  `format_html` in `render_advisory_url`
- `src/django_apps/inventory/sbom/pages.py` — `versions_tab_context`, registered in
  `TAB_CONTEXT_BUILDERS`
- `tests/unit/test_vulnerabilities_tab.py` — regression test for the advisory-URL crash
- `tests/unit/test_results_page.py` — placeholder check replaced by a no-placeholders-remain check
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Filled in the Version Currency tab, completing the four detail tabs: seven columns in Story 8.23's order with PyPI Latest adjacent to conda-forge Latest, registry links per ecosystem (plain text when unknown), divergence flagging, and all three LTS states. Status sorts by class rank rather than alphabetically, asserted as an exact rendered sequence because an alphabetical sort looks plausible and buries the most outdated packages. Fixed a latent `format_html` crash that also existed in Story 21.14's advisory column and covered it with a regression test. `pixi run ci` exit 0; 733 backend tests at 96.56%. |
