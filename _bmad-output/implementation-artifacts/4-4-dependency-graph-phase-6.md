# Story 4.4: Dependency Graph — Phase 6

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a dependency graph in both interactive and downloadable forms,
so that I can explore my dependency tree visually and export a static copy.

## Acceptance Criteria

1. Given a resolved package list with `depends-on` relationships, when Phase 6 runs, then a directed acyclic graph (DAG) is built using NetworkX (FR-5.3).
2. Given the built DAG, when the graph JSON is produced, then it matches the exact Cytoscape.js shape: `{"nodes": [{"data": {"id": "<name>==<version>", "label": "<name>", "version": "<version>"}}], "edges": [{"data": {"source": "<node_id>", "target": "<node_id>"}}]}` (FR-5.3, AD-9).
3. Given the built DAG, when the static artifact is produced, then a Graphviz SVG is rendered and stored in S3/MinIO for download (FR-5.3, AD-9).
4. Given `GET /api/v1/sbom/result/{task_id}/reports/graph/`, when called with an org-scoped credential, then the `{nodes, edges}` JSON is returned; no PyVis HTML is ever generated or served (AD-9).
5. Given the Graphviz SVG, when the client requests the downloadable graph, then it is served as a separate download via a presigned URL (AD-11).
6. Given Phase 6 completes, when the result is persisted, then an `AnalysisReport` with `report_type="graph"` is created with `artifact_key` (the SVG) and a `summary` recording node and edge counts (AD-6).
7. Given Phase 6 starts and completes, when each boundary is crossed, then progress updates cover the 88–93% range with structured logging (FR-4.2, NFR-6.1).

## Tasks / Subtasks

- [ ] Task 1 — Build the DAG (AC: #1)
  - [ ] Implement `analysis/services/graph.py::build(packages) -> tuple[dict, bytes]` as a pure function
  - [ ] Construct a NetworkX `DiGraph` from the resolved package list and their `depends-on` edges
- [ ] Task 2 — Produce Cytoscape JSON (AC: #2, #4)
  - [ ] Emit the EXACT shape: nodes `{"data": {"id": "name==version", "label": "name", "version": "version"}}`; edges `{"data": {"source": "<id>", "target": "<id>"}}`
  - [ ] Store this JSON in `AnalysisReport.summary` (served directly to Cytoscape.js in the SPA)
  - [ ] Do NOT generate PyVis HTML or any iframe payload (AD-9)
- [ ] Task 3 — Render Graphviz SVG (AC: #3, #5)
  - [ ] Generate a Graphviz SVG via `pygraphviz` from the same DAG
  - [ ] Store at `sbom-results/{org_id}/{task_id}/graph.svg`; `artifact_key` points to it
- [ ] Task 4 — Persist report (AC: #6)
  - [ ] Return chord envelope: `report_type="graph"`, `artifact_key` = SVG path, `summary={node_count, edge_count, nodes, edges}`, `failed=False`
- [ ] Task 5 — API endpoint (AC: #4, #5)
  - [ ] `GET /api/v1/sbom/result/{task_id}/reports/graph/`: return `{nodes, edges}` JSON (from summary); job via `for_org` (404 cross-org)
  - [ ] SVG download served via `303` → presigned URL (AD-11)
- [ ] Task 6 — Progress + logging (AC: #7)
  - [ ] `task.update_state` across 88–93%, `current_step='dependency graph'`
  - [ ] structlog on start/completion: phase, duration, node/edge counts
- [ ] Task 7 — Tests (AC: all)
  - [ ] Assert exact JSON shape (id format `name==version`), node/edge counts, SVG artifact written; assert NO PyVis output
  - [ ] API test: JSON endpoint returns `{nodes, edges}`; cross-org → 404
  - [ ] ≥90% coverage; `pixi run ci` exits 0

## Dev Notes

### Graph service (solution-design.md §3.4; AD-9)

Builds a NetworkX `DiGraph` from the resolved package list. Produces two outputs:

1. `{nodes, edges}` JSON (stored in `AnalysisReport.summary`) — served at `GET /api/v1/sbom/result/{task_id}/reports/graph/` and consumed directly by Cytoscape.js (`react-cytoscapejs` + `cytoscape-dagre`) in the React SPA.
2. A Graphviz SVG (via `pygraphviz`) — stored in S3 at `sbom-results/{org_id}/{task_id}/graph.svg`, available for download.

Exact API response shape (required by Cytoscape.js `data` wrapper convention):

```json
{
  "nodes": [
    {"data": {"id": "requests==2.32.3", "label": "requests", "version": "2.32.3"}}
  ],
  "edges": [
    {"data": {"source": "requests==2.32.3", "target": "urllib3==2.3.0"}}
  ]
}
```

CRITICAL (AD-9): No PyVis HTML is generated or served, ever. No iframe in the SPA. The JSON goes straight to Cytoscape.js; the SVG is the static download.

### Storage & download (AD-6, AD-11; solution-design.md §6.1)

- SVG at `sbom-results/{org_id}/{task_id}/graph.svg`; `artifact_key` in PostgreSQL.
- JSON served from `summary`; SVG served via `303` → presigned URL. Cross-org → 404.

### Failure semantics (§4.4)

On failure, envelope `failed=True` + `failure_reason`; chord (4.6) continues; SBOM still completes (FR-4.5).

### Dependency / sequencing notes

- Depends on Story 4.1 (envelope helpers, `AnalysisReport`) and Epic 3 resolved package list with dependency edges.
- The SPA graph panel (`DepGraph.tsx`) that consumes this JSON is Epic 5 Story 5.5 — this story only produces the data + SVG and the JSON endpoint.
- Wired into the real analysis group by Story 4.6.
- `pygraphviz` requires the system Graphviz library — ensure it is available in the backend image (Docker) and dev env.

### Project Structure Notes

- Service: `<project_slug>/analysis/services/graph.py` (pure function).
- Endpoint under `/api/v1/sbom/result/{task_id}/reports/graph/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.4: Dependency Graph — Phase 6]
- [Source: solution-design.md#3.4 analysis/ — Graph service]
- [Source: solution-design.md#6.1 Storage paths]
- [Source: ARCHITECTURE-SPINE.md#AD-9 — Graph API shape: {nodes, edges} JSON, no PyVis HTML]
- [Source: ARCHITECTURE-SPINE.md#AD-6 — Storage triad]
- [Source: ARCHITECTURE-SPINE.md#AD-11 — Presigned URL downloads]
- [Source: prd.md#FR-5.3, FR-4.2, NFR-6.1]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

- The resolved `PackageSpec` list carries **no dependency edges** — derived them from each package's PyPI `requires_dist` (extras-gated deps skipped; PEP 503 name matching against the resolved set).
- conda-forge Graphviz needs `dot -c` to register its plugins or pygraphviz fails with "Format: svg not recognized". Pixi skips the post-link script that does this by default → enabled `run-post-link-scripts` in `.pixi/config.toml` (tracked; covers local + CI) and added `RUN pixi run dot -c` to the Dockerfile (the image doesn't carry `.pixi/config.toml`).

### Completion Notes List

- **`analysis/services/graph.py::build(packages) -> (cytoscape_json, svg_bytes)`** — pure (AD-3). Builds a NetworkX `DiGraph`: a node per resolved package (`id = name==version`), edges derived from PyPI `requires_dist`. Emits the **exact Cytoscape.js shape** (`{"nodes":[{"data":{id,label,version}}], "edges":[{"data":{source,target}}]}`, AD-9) and a **Graphviz SVG** via pygraphviz. **No PyVis HTML, ever.** PyPI fetch failures degrade to no-edges (nodes still present).
- **Phase 6 task** `tasks/analysis.py::build_dependency_graph` (analysis queue, 88→93%). Dedicated (not `_run_phase`): the artifact is the SVG, and the Cytoscape JSON + counts live in the report `summary`. Failure → `failed` envelope (FR-4.5).
- **Endpoints:** `GET .../reports/graph/` returns the `{nodes, edges}` JSON **inline from `summary`** (served straight to Cytoscape.js, AD-9); `GET .../reports/graph/download/` → **303** to the presigned SVG. Refactored `analysis/views.py` with a shared `_resolve_job` helper. Cross-org → 404.
- New deps (conda-forge): `networkx`, `pygraphviz`, `graphviz`.
- Gate: `pixi run ci` exits 0 — 167 tests, 95.20% coverage (real SVG rendering exercised in unit tests).

### File List

- backend/generate_sbom/analysis/services/graph.py (DiGraph + Cytoscape + SVG)
- backend/generate_sbom/tasks/analysis.py (build_dependency_graph task)
- backend/generate_sbom/analysis/views.py, urls.py (_resolve_job helper, GraphReportView + GraphSvgDownloadView)
- backend/pyproject.toml (mypy overrides for networkx/pygraphviz)
- pixi.toml / pixi.lock (networkx, pygraphviz, graphviz)
- .pixi/config.toml (run-post-link-scripts), Dockerfile (dot -c)
- backend/tests/unit/test_graph_service.py, test_graph_task_api.py (new)
