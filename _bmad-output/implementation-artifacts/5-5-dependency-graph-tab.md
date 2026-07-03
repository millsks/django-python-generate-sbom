# Story 5.5: Dependency Graph Tab

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want an interactive dependency graph with a download option,
so that I can explore my dependency tree and export a static copy.

## Acceptance Criteria

1. Given a job with graph data, when I view the Dependency Graph tab, then the graph renders inline using Cytoscape.js with a hierarchical dagre layout, consuming the `{nodes, edges}` JSON from the graph endpoint.
2. Given the rendered graph, when I interact with it, then zoom, pan, node drag, and hover-to-highlight all work.
3. Given the Dependency Graph tab, when I click "Download SVG", then the static Graphviz SVG artifact downloads (via presigned URL).
4. Given the graph tab uses Cytoscape.js, when it renders, then no PyVis HTML or iframe is used.
5. Given the graph phase failed, when I view the tab, then a failure notice with the reason is shown.

## Tasks / Subtasks

- [ ] Task 1 — Fetch graph JSON (AC: #1)
  - [ ] Call `api/reports.getGraph(taskId)` → `GET /api/v1/sbom/result/{taskId}/reports/graph/` returning `{nodes, edges}` in the exact Cytoscape shape (AD-9)
- [ ] Task 2 — `DepGraph.tsx` component (AC: #1, #2, #4)
  - [ ] Wrap `react-cytoscapejs` (`CytoscapeComponent`) with `cytoscape-dagre` layout `{ name: 'dagre', rankDir: 'TB' }`
  - [ ] Register the dagre layout extension with cytoscape once at module load
  - [ ] Pass elements via `CytoscapeComponent.normalizeElements({ nodes, edges })`
  - [ ] Style container `{ width: '100%', height: 600 }`
  - [ ] Enable interactions: zoom, pan, node drag (Cytoscape defaults) and add hover-to-highlight (mouseover/mouseout handlers highlighting a node and its edges)
  - [ ] No iframe, no PyVis HTML anywhere (AD-9)
- [ ] Task 3 — Download SVG (AC: #3)
  - [ ] "Download SVG" button hits the graph SVG artifact via presigned URL (`sbom-results/{org_id}/{task_id}/graph.svg`) — reuse the api download helper pattern (303 → presigned, AD-11)
- [ ] Task 4 — Lazy mount for performance (AC: #1)
  - [ ] Mount the graph panel only when the tab is activated (graph rendering is explicitly excluded from the NFR-2.2 <3s page-load budget) — keep the rest of ResultsPage fast
- [ ] Task 5 — Failure notice (AC: #5)
  - [ ] If the graph report `failed`, render the shared `TabFailureNotice` with `failure_reason`
- [ ] Task 6 — Tests (AC: #1, #4, #5)
  - [ ] Component test: given sample `{nodes, edges}`, the CytoscapeComponent receives normalized elements with the dagre layout
  - [ ] Assert no iframe / no PyVis in the rendered output
  - [ ] Failed report renders the failure notice

## Dev Notes

### Cytoscape wrapper (solution-design.md §7.3; AD-9)

```tsx
<CytoscapeComponent
  elements={CytoscapeComponent.normalizeElements({
    nodes: graphData.nodes,
    edges: graphData.edges,
  })}
  layout={{ name: 'dagre', rankDir: 'TB' }}
  style={{ width: '100%', height: 600 }}
/>
```

Graph JSON shape (AD-9, exact):

```json
{
  "nodes": [{"data": {"id": "requests==2.32.3", "label": "requests", "version": "2.32.3"}}],
  "edges": [{"data": {"source": "requests==2.32.3", "target": "urllib3==2.3.0"}}]
}
```

No iframe, no PyVis HTML — Cytoscape.js only. [Source: ARCHITECTURE-SPINE.md AD-9; solution-design.md §7.3]

### Stack (installed in Story 1.4)

cytoscape 3.34.0, react-cytoscapejs 2.0.0, cytoscape-dagre 4.0.0. Register the dagre extension: `cytoscape.use(dagre)`. [Source: solution-design.md §7.1; implementation-artifacts/1-4-react-spa-foundation.md]

### SVG download (AD-11)

The static Graphviz SVG is produced by Epic 4 Story 4.4 and stored at `sbom-results/{org_id}/{task_id}/graph.svg`; download via 303 → presigned URL. [Source: solution-design.md §3.4 graph service, §6.1, §6.2]

### Performance

Graph rendering is excluded from the NFR-2.2 <3s budget; lazy-mount the panel on tab activation so it doesn't slow initial page load. [Source: epics.md#Story 5.1 AC6; prd.md NFR-2.2]

### Dependency / sequencing

Depends on Story 5.1 (shell + api layer) and consumes the Epic 4 Story 4.4 graph endpoint + SVG artifact. Independent of other tabs. [Source: epics.md#Epic 5]

### Project Structure Notes

- `frontend/src/components/DepGraph.tsx` (Cytoscape wrapper); tab panel wires it into ResultsPage; fetcher in `frontend/src/api/reports.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.5: Dependency Graph Tab]
- [Source: ARCHITECTURE-SPINE.md#AD-9 — Graph API shape: {nodes, edges} JSON, no PyVis]
- [Source: ARCHITECTURE-SPINE.md#AD-11 — Artifact downloads via presigned URL]
- [Source: solution-design.md#7.3 Dependency graph panel]
- [Source: solution-design.md#3.4 analysis/ — Graph service]
- [Source: prd.md#FR-6.5, FR-5.3, FR-6.7]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
