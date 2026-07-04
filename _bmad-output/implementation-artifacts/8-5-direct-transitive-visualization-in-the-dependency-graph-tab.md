# Story 8.5: Direct/Transitive Visualization in the Dependency Graph Tab

Status: review

<!-- Contexted from the 8.2 spike: planning-artifacts/research/direct-vs-transitive-design.md -->

## Story

As a user,
I want direct dependencies visually distinct from transitive ones in the graph,
so that I can see my declared surface at a glance.

## Acceptance Criteria

1. Given the graph service builds Cytoscape `{nodes, edges}`, when a node is built from a `PackageSpec`, then the node data carries its `relationship` (`direct` / `transitive` / `unknown`).
2. Given the dependency-graph tab, when it renders a job that carries the relationship, then direct nodes are visually distinguished from transitive ones (e.g. highlighted/rooted vs. faded) with a legend.
3. Given nodes tagged `unknown` (e.g. a `pixi.lock` job), when the graph renders, then they render in a neutral style (no false direct/transitive claim).
4. Given a job generated before this feature (nodes without a `relationship`), when its graph renders, then it degrades gracefully — neutral styling, no crash.

## Tasks / Subtasks

- [ ] Task 1 — Graph node data (AC: #1)
  - [ ] In `analysis/services/graph.py`, include `relationship` in each node's `data` (read from the `PackageSpec`)
  - [ ] Backend test: node data carries the relationship
- [ ] Task 2 — Frontend types (AC: #1)
  - [ ] Add `relationship?: string` to the graph node type in `frontend/src/api/reports.ts`
- [ ] Task 3 — DepGraph styling + legend (AC: #2, #3, #4)
  - [ ] In `DepGraph.tsx`, style nodes by `relationship`: direct = highlighted (e.g. bold border / accent color), transitive = faded, unknown/absent = neutral
  - [ ] Add a small legend mapping the styles
- [ ] Task 4 — Tests
  - [ ] Frontend: nodes get the relationship-based style class; legend renders; a graph with no relationship data renders neutrally (no crash)
  - [ ] `pixi run ci` exits 0

## Dev Notes

### Data flow (from the 8.2 spike)

`PackageSpec.relationship` (Story 8.3) flows into the graph service, which already
takes `list[PackageSpec]` and builds Cytoscape node data. Surface it in the node
`data` so the SPA can style by it. [Source:
research/direct-vs-transitive-design.md#Downstream story impact;
backend/generate_sbom/analysis/services/graph.py]

### Graceful degradation (AC #4)

Older jobs' graph JSON has no `relationship` on nodes; treat missing as `unknown`
and render neutrally — never crash. Mirrors the SBOM viewer's optional-column
handling (8.6). [Source: research/direct-vs-transitive-design.md#Decision 4]

### Dependency on 8.3

Requires `PackageSpec.relationship` (Story 8.3). Independent of 8.4 (SBOM encoding)
— the graph reads the flag from the spec, not from the SBOM document.

### References

- [Source: _bmad-output/planning-artifacts/research/direct-vs-transitive-design.md]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.5]
- [Source: backend/generate_sbom/analysis/services/graph.py]
- [Source: frontend/src/components/DepGraph.tsx, frontend/src/api/reports.ts]
- [Source: prd.md#FR-6.5]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

### Completion Notes List

- **Backend:** `graph.build` now stores `pkg.relationship` as a node attribute and `_to_cytoscape` exposes it in each node's `data` (`direct`/`transitive`/`unknown`). Verified the Graphviz SVG still renders with the extra attribute.
- **Frontend:** `DepGraph` styles nodes by relationship via Cytoscape data selectors — **direct** = green + bold border (rooted/highlighted), **transitive** = faded grey, **unknown/missing** = neutral blue (base style). A legend (Direct / Transitive) shows only when relationship data is present.
- **Graceful degradation (AC #4):** older graphs whose nodes lack `relationship` match no relationship selector → neutral base style, and the legend is hidden — no crash.
- **Tests:** backend — node data carries the relationship; frontend — legend shows with data, hidden without.
- Gate: `pixi run ci` exits 0 — backend 242 (93.95%), frontend 46.

### File List

- backend/generate_sbom/analysis/services/graph.py (relationship in node data)
- backend/tests/unit/test_graph_service.py (relationship test + updated exact-node assertion)
- frontend/src/api/reports.ts (GraphNode.relationship), components/DepGraph.tsx (styling + legend), DepGraph.test.tsx
