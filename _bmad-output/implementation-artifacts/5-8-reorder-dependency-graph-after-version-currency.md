# Story 5.8: Move the Dependency Graph Tab to the Right of Version Currency

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user of the SBOM Results page,
I want the Dependency Graph tab to sit to the right of Version Currency (last in the bar),
so that the tab order reflects each report's importance and the graph — the least
central of the reports — comes last instead of ahead of Version Currency.

## Context / root cause

On the Results page tab bar the last two tabs are currently **Dependency Graph** then
**Version Currency** (`ResultsPage.tsx:32-33`). Kevin's request (2026-07-05): the graph is
less important than the other reports and should come last, so the order should be
**Overview · SBOM · Vulnerabilities · Licenses · Version Currency · Dependency Graph** —
the last two swapped. Low-priority UX polish, but the swap touches index-coupled code:
the tabs are rendered by array position, the `TabPanel` bodies are index-based, and the
Overview quick-nav cards jump to hard-coded tab indices, so a header-only swap would
mis-wire the panels. Frontend-only; no API changes (AD-5).

## Acceptance Criteria

1. Given the Results tab bar, when the page renders, then the tabs read **Overview · SBOM · Vulnerabilities · Licenses · Version Currency · Dependency Graph** — Version Currency before Dependency Graph, with Dependency Graph last.
2. Given the reordered tab bar, when I select any tab, then the correct report renders — Version Currency shows the version currency table and Dependency Graph shows the graph — with each `TabPanel` body's index still matching its header (header↔panel alignment preserved, no cross-wiring).
3. Given the Overview quick-nav metric cards, when I click the "Version currency" card, then it still jumps to the Version Currency tab (now at its new index), and the Vulnerabilities and Licenses cards still jump to their unchanged tabs.
4. Given the reorder, when complete, then there is no regression to deep-linking or Excel export ordering — the active tab is held in local component state only (no URL/deep-link coupling) and the "Export all to Excel" sheet order is independent of the tab array; both are stated explicitly in Dev Notes and left unchanged.
5. Given the change, when tests run, then the `ResultsPage` tab-order assertion and any Overview quick-nav index assertion are updated to the new order, and `pixi run ci` is green.

## Tasks / Subtasks

- [ ] Task 1 — Swap the tab headers (AC: #1)
  - [ ] In `frontend/src/pages/ResultsPage.tsx`, in the `TABS` array (`ResultsPage.tsx:27-34`), swap the last two entries so `{ label: 'Version Currency', Icon: TabIcon.versions }` precedes `{ label: 'Dependency Graph', Icon: TabIcon.graph }`
- [ ] Task 2 — Realign the panel bodies (AC: #2)
  - [ ] In the same file, swap the two matching `TabPanel` blocks (`ResultsPage.tsx:145-150`) so `index={4}` renders `<VersionsTab taskId={taskId!} />` and `index={5}` renders `<DepGraph taskId={taskId!} />` — keeping every header at its panel index
- [ ] Task 3 — Fix the Overview quick-nav index (AC: #3)
  - [ ] In `frontend/src/components/OverviewTab.tsx`, update the `TAB` index map (`OverviewTab.tsx:20`) so `versions` is `4` (was `5`); `vulnerabilities` (2) and `licenses` (3) are unchanged. Dependency Graph has no quick-nav card, so no card index is added
- [ ] Task 4 — Tests (AC: #5)
  - [ ] `frontend/src/pages/ResultsPage.test.tsx` (~lines 61-68): update the expected tab-order array so the last two labels are `'Version Currency'` then `'Dependency Graph'`
  - [ ] `frontend/src/components/OverviewTab.test.tsx`: the existing quick-nav test only pins the Vulnerabilities card → `onNavigate(2)` (line 83). Add (or extend) an assertion that the Version currency card calls `onNavigate(4)` so the new index is guarded; the export sheet-name assertions (lines 95, 107) stay unchanged (they verify export order, not tab order)
- [ ] Task 5 — Gate (AC: #5)
  - [ ] Frontend lints (oxlint) and builds (tsc + vite); `pixi run ci` exits 0

## Dev Notes

### Index realignment (the crux)

The tab bar and its panels are position-indexed, so three coupled edits must land together:

| Concern | Location | Before | After |
| --- | --- | --- | --- |
| Tab header order | `ResultsPage.tsx:27-34` (`TABS`) | idx 4 Dependency Graph, idx 5 Version Currency | idx 4 Version Currency, idx 5 Dependency Graph |
| Panel bodies | `ResultsPage.tsx:145-150` (`TabPanel`) | idx 4 `<DepGraph>`, idx 5 `<VersionsTab>` | idx 4 `<VersionsTab>`, idx 5 `<DepGraph>` |
| Overview quick-nav | `OverviewTab.tsx:20` (`TAB`) | `versions: 5` | `versions: 4` |

Version Currency moves 5→4 and Dependency Graph 4→5. `vulnerabilities: 2` and `licenses: 3`
are untouched. Swapping only the header array without also swapping the `TabPanel` bodies
would show the graph under the "Version Currency" header (and vice-versa) — Task 1 and
Task 2 are a single logical change and must be made together.

### No deep-link / URL coupling (AC #4)

The active tab is held in local state only — `const [tab, setTab] = useState(0)`
(`ResultsPage.tsx:56`); there is **no** query param, hash, or router state that encodes the
tab index. Reordering therefore does **not** break any existing deep link — none exist. No
change to routing is required or made.

### Export ordering is independent (AC #4)

The "Export all to Excel" workbook order is **not** derived from the tab array. `exportAll`
in `OverviewTab.tsx` fetches and pushes sheets in a fixed sequence — versions, then
vulnerabilities, then licenses (`OverviewTab.tsx:76-84`) — and `reportSheets.ts` only defines
per-report sheet builders, decoupled from any tab index. The user asked to move the on-screen
tab only, so the export order is left unchanged; the existing sheet-name test assertions
(`OverviewTab.test.tsx:95,107` → `['Version Currency', 'Vulnerabilities', 'Licenses']`) remain
valid and are a good confirmation that export order and tab order are not coupled.

### Conventions

- Frontend-only; lives in `frontend/src/pages/ResultsPage.tsx` and
  `frontend/src/components/OverviewTab.tsx`. No API-layer or backend changes (AD-5).
- No new components; `DepGraph`, `VersionsTab`, and `TabIcon.graph`/`TabIcon.versions` are
  reused as-is — only their order/index changes.

### Dependency / sequencing

Builds on Story 5.1 (tab shell), 5.5 (Dependency Graph tab), and 5.6 (Version Currency tab),
all done. Independent of every other in-flight epic. [Source: epics.md#Epic 5]

### Project Structure Notes

- `frontend/src/pages/ResultsPage.tsx` — tab definitions + panel bodies.
- `frontend/src/components/OverviewTab.tsx` — quick-nav index map.
- Tests: `frontend/src/pages/ResultsPage.test.tsx`, `frontend/src/components/OverviewTab.test.tsx`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.8: Move the Dependency Graph Tab to the Right of Version Currency]
- [Source: Kevin request (2026-07-05) — graph is less important; move it last on the tab bar]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA: REST API only]
- [Source: epics.md#Story 5.1 (shell), #Story 5.5 (graph), #Story 5.6 (version currency)]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
