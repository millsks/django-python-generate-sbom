# Story 20.1: Retire the Dependency Graph

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **First story of Epic 20 — build it first.** Retiring the dependency-graph visualization removes the
> `networkx` / `pygraphviz` / `graphviz` conda dependencies, which are the fragile pieces blocking a clean
> `win-64` solve (Story 20.2). Do this before adding the Windows platform. **Full Epic 20 build order:
> 20.1 → 20.2 → 20.3 → 20.4 → 20.5 → 20.6 → 20.7.**

> **Dependency removals are user-approved.** Dropping `networkx`, `pygraphviz`, and `graphviz` from `pixi.toml`
> is an explicitly approved removal (no add-dependency sign-off gate applies — that gate is for *new* runtime
> deps). Removing them is in scope here.

> **⚠ PRESERVE the direct/transitive DATA.** Only the *visualization* is retired. The direct vs. transitive
> relationship data lives in the SBOM document (Stories 8.3–8.5, 8.26) and the SBOM viewer tab — do **not**
> touch it. The graph service merely *read* that data for node coloring.

## Story

As the product owner,
I want the dependency-graph report, endpoints, tab, and its heavyweight visualization libraries removed,
so that the least-used report (unreadable at scale) stops carrying the cross-platform-hostile `pygraphviz`/
`graphviz` build and the app's footprint shrinks.

## Acceptance Criteria

1. **Backend graph service, phase & task removed.**
   Given Phase 6 builds a networkx graph and renders SVG via pygraphviz, when the graph is retired, then
   `backend/generate_sbom/analysis/services/graph.py` is deleted, the `build_dependency_graph` Celery task
   (`backend/generate_sbom/tasks/analysis.py` L137–178 and its import at L25) is removed, and it is dropped
   from the `analysis_group` in `backend/generate_sbom/tasks/sbom_pipeline.py` (import L33, group member L94) —
   leaving the analysis group with the three remaining phases (vulnerabilities, licenses, version currency).
2. **`GRAPH` report type & endpoints removed.**
   Given the `ReportType.GRAPH` enum and its two endpoints, when the graph is retired, then `GRAPH` is removed
   from `backend/generate_sbom/analysis/models.py` (L19); a `analysis` migration is generated (choice-only
   `AlterField` on `report_type`, mirroring the Story 15.3 migration pattern — `max_length=10` unchanged, the
   remaining longest value `version` still fits); `GraphReportView` and `GraphSvgDownloadView`
   (`analysis/views.py` L138–158), their two URL routes (`reports/graph/`, `reports/graph/download/` —
   `analysis/urls.py` L5–9, L24–33), and `GraphReportResponseSerializer` (`analysis/serializers.py` L15–19)
   are removed.
3. **Graph libraries removed from pixi + Docker + mypy config.**
   Given the three libraries are graph-only (verified: the sole consumer was `services/graph.py`), when the
   graph is retired, then `networkx` (`pixi.toml` L39), `pygraphviz` (L40), and `graphviz` (L41) are removed
   from `[dependencies]`; the `pixi run dot -c` Graphviz-plugin registration step is removed from the
   `Dockerfile` (L15–18); the `networkx.*` / `pygraphviz.*` mypy `ignore_missing_imports` overrides are removed
   from `backend/pyproject.toml` (L66–67); and `pixi.lock` is re-solved.
4. **Frontend Dependency Graph tab & Cytoscape removed.**
   Given the Dependency Graph tab is the last tab (index 5, per Story 5.8), when the graph is retired, then
   `frontend/src/components/DepGraph.tsx`, `DepGraph.test.tsx`, and `frontend/src/react-cytoscapejs.d.ts` are
   deleted; the tab is removed from `frontend/src/pages/ResultsPage.tsx` (import L23, `TABS` entry L33, and the
   `<TabPanel index={5}>` at L148–150) — **tab indices 0–4 are unchanged** (Overview, SBOM viewer,
   Vulnerabilities, Licenses, Version Currency stay put); `cytoscape`, `cytoscape-dagre`, and
   `react-cytoscapejs` are removed from `frontend/package.json` (L20, L21, L24) and the lockfile; and the
   graph types/helpers (`GraphNode`/`GraphEdge`/`GraphReport`, `getGraph`, `graphSvgDownloadUrl`) are removed
   from `frontend/src/api/reports.ts` (L1, L40–50, L78–85).
5. **Overview & landing references cleaned.**
   Given the Overview tab has **no** graph metric or quick-nav (verified — `OverviewTab.tsx` `TAB` maps only
   vulnerabilities/licenses/versions), when the graph is retired, then no Overview change is required beyond
   confirming nothing references it; the HomePage feature list and hero copy
   (`frontend/src/pages/HomePage.tsx` L29, L37, L79–80) drop the "dependency graph" mentions; and the now-unused
   `graph: AccountTreeIcon` entry in `frontend/src/icons.ts` (L69) is removed.
6. **Docs & report count updated.**
   Given the docs describe the graph as a report/feature, when the graph is retired, then all graph mentions
   are removed and the report count is decremented **wherever it appears** — notably `docs/developer/data-model.md`
   (L73–75, "up to **four** reports" → "**three**"); plus `docs/index.md` L9, `README.md` L6/L42,
   `docs/user-guide/index.md` L12, `docs/user-guide/reading-the-results.md` L7/L49–51,
   `docs/how-to/generate-sbom.md` L28, `docs/developer/index.md` L23, `docs/developer/project-layout.md` L25,
   `docs/developer/pipeline.md` L28/L47 (Phase 6 section), `docs/api/index.md` L64–65,
   `docs/api/analysis.md` L85–98, and `docs/api/artifacts.md` L45–55.
7. **Direct/transitive data preserved + gate green.**
   Given the SBOM document still encodes direct/transitive relationships, when the graph is retired, then
   `backend/generate_sbom/sbom/parsers/_types.py`, `sbom/generation.py`, and `sbom/document.py` are
   **untouched**, the SBOM viewer tab still shows direct/transitive, and `pixi run ci` is green with the
   graph-only tests removed (`test_graph_service.py`, `test_graph_task_api.py` deleted; `ResultsPage.test.tsx`
   and any analysis-group/pipeline tests that asserted the graph task are updated to the 3-report group) and
   backend coverage ≥90%.

## Tasks / Subtasks

- [ ] **Task 1 — Backend service/task/pipeline (AC: #1)** — Delete `analysis/services/graph.py`; remove
  `build_dependency_graph` and its import from `tasks/analysis.py`; drop it from the `analysis_group` in
  `tasks/sbom_pipeline.py` (import + group member). Confirm the group now fans out to 3 tasks.
- [ ] **Task 2 — Enum, migration, endpoints, serializer (AC: #2)** — Remove `ReportType.GRAPH`; run
  `makemigrations analysis` (choice-only `AlterField`) and commit it; delete `GraphReportView`,
  `GraphSvgDownloadView`, their URL routes, and `GraphReportResponseSerializer`.
- [ ] **Task 3 — pixi / Docker / mypy (AC: #3)** — Remove `networkx`/`pygraphviz`/`graphviz` from `pixi.toml`;
  remove the `pixi run dot -c` step from the `Dockerfile`; remove the `networkx.*`/`pygraphviz.*` mypy
  overrides from `backend/pyproject.toml`; re-run `pixi install` to re-solve `pixi.lock`.
- [ ] **Task 4 — Frontend tab & deps (AC: #4, #5)** — Delete `DepGraph.tsx`, `DepGraph.test.tsx`,
  `react-cytoscapejs.d.ts`; strip the tab from `ResultsPage.tsx` (import, `TABS` entry, `TabPanel index 5`);
  remove `cytoscape`/`cytoscape-dagre`/`react-cytoscapejs` from `package.json` + lockfile; remove the graph
  types/helpers from `api/reports.ts`; drop the HomePage graph copy and the `graph` icon entry.
- [ ] **Task 5 — Docs + count (AC: #6)** — Remove graph mentions across `docs/**` + `README.md`; decrement the
  report count wherever it appears (data-model "four" → "three"; drop the graph from feature/report lists).
- [ ] **Task 6 — Tests + gate (AC: #7)** — Delete `test_graph_service.py` and `test_graph_task_api.py`; update
  `ResultsPage.test.tsx` and any pipeline/analysis-group test asserting the graph task; confirm the SBOM
  viewer's direct/transitive still renders; run `pixi run ci` to green (backend coverage ≥90%).

## Dev Notes

### Retirement footprint — verified

The three libraries are **truly graph-only**: the sole importer of `networkx`/`pygraphviz` is
`analysis/services/graph.py` (`_to_cytoscape` at L56, `_render_svg` at L73–77, `nx.DiGraph()` at L86), and
the `Dockerfile`'s `pixi run dot -c` (L15–18) exists only to register Graphviz plugins for pygraphviz's SVG
rendering. Nothing else in the backend imports them.

### What stays — the direct/transitive data (do NOT touch)

The authoritative direct/transitive data is produced by the parsers and written into the SBOM document, wholly
independent of the graph visualization:
- `sbom/parsers/_types.py` — `DIRECT`/`TRANSITIVE` constants (L12–13), `PackageSpec.relationship` (L29),
  `tag_relationships` (L33–42, Story 8.3 / AD-14).
- `sbom/generation.py` — writes `sbom:relationship` per component (L132) and CycloneDX/SPDX `DEPENDS_ON`
  (L141–145, L195–220, Story 8.4).
- `sbom/document.py` — parses `relationship` back out for the SBOM viewer (L223–233, L300–320, L347–368).

The Phase-6 `summary` payload (`node_count`/`edge_count`/`nodes`/`edges`, `tasks/analysis.py` L155–160) is
Cytoscape-shaped *visualization* data — NOT the authoritative relationship data — and is safe to drop.

### Tab re-indexing — verified

Results tabs are: 0 Overview, 1 SBOM viewer, 2 Vulnerabilities, 3 Licenses, 4 Version Currency, 5 Dependency
Graph (moved last by Story 5.8). Removing the graph drops **only** index 5; indices 0–4 are untouched, and
`OverviewTab.tsx`'s quick-nav (`{vulnerabilities:2, licenses:3, versions:4}`) needs no change.

### Migration note

`report_type` is `max_length=10`; removing the `GRAPH` choice is a choice-only `AlterField` (same shape as the
Story 15.3 migration). The remaining longest value (`version`) still fits — no length change.

### Testing standards

- Backend: delete the two graph-only unit tests; update any `analysis_group`/pipeline test that asserted four
  fan-out tasks to expect three. Coverage ≥90% via `pixi run ci`.
- Frontend: delete `DepGraph.test.tsx`; update `ResultsPage.test.tsx` to the 5-tab layout.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.1: Retire the Dependency Graph]
- Backend: `analysis/services/graph.py`, `tasks/analysis.py` (L25, L137–178), `tasks/sbom_pipeline.py`
  (L33, L94), `analysis/models.py` (L19), `analysis/views.py` (L138–158), `analysis/urls.py` (L5–9, L24–33),
  `analysis/serializers.py` (L15–19), `backend/pyproject.toml` (L66–67).
- Frontend: `components/DepGraph.tsx`, `DepGraph.test.tsx`, `react-cytoscapejs.d.ts`, `pages/ResultsPage.tsx`
  (L23, L33, L148–150), `api/reports.ts` (L40–50, L78–85), `icons.ts` (L69), `pages/HomePage.tsx`
  (L29, L37, L79–80), `frontend/package.json` (L20, L21, L24).
- Config: `pixi.toml` (L39–41), `Dockerfile` (L15–18).
- Preserve: `sbom/parsers/_types.py`, `sbom/generation.py`, `sbom/document.py` (untouched).
- Downstream: `20-2-add-win-64-platform-and-verify-env.md` (the removed libs unblock the `win-64` solve).

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
