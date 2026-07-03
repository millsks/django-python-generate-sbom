# Adversarial Review — django-python-generate-sbom Architecture Spine

## Verdict

Six incompatible pairs found — four are genuine AD gaps requiring new or tightened rules before stories can be written safely.

---

## Incompatible Pairs

### Gap 1 — Manifest upload storage path (manifests/ vs sbom/)

**Pair:** `manifests/` (writes uploaded file) vs `sbom/services.py` (reads file by key to start Phase 1)

**Divergence scenario:** `manifests/` stores the upload at `uploads/{upload_id}/{filename}`. `sbom/` expects it at `manifests/{org_id}/{upload_id}/{filename}`. Both comply with AD-6 (no blob in DB/Redis) and AD-2 (org scoping), but `sbom/` cannot find the file.

**Gap:** AD-6 specifies artifact output paths (`sbom-results/{org_id}/{task_id}/...`) but nothing specifies the manifest *upload* storage path pattern.

**Fix needed:** New AD or Convention row fixing: `manifest-uploads/{org_id}/{upload_id}/{original_filename}`.

---

### Gap 2 — Chord callback inter-task result envelope (pipeline worker vs analysis worker)

**Pair:** `tasks/analysis.py` (4 parallel analysis tasks returning results) vs `tasks/sbom_pipeline.py` (chord callback aggregating them)

**Divergence scenario:** `vulnerability.py` task returns `{"vulnerabilities": [...], "scan_complete": true}`. Chord callback in `sbom_pipeline.py` expects `{"vuln_results": [...], "status": "ok"}`. Both follow AD-4 (correct queues), AD-3 (pure service functions), AD-6 (no blobs in result). The aggregation silently fails or raises a KeyError.

**Gap:** AD-9 fixes the graph output shape. Nothing fixes the result envelope for the other 3 analysis tasks.

**Fix needed:** Convention row specifying the chord result envelope: `{"type": "<vuln|license|graph|version>", "artifact_key": "<s3-path>", "summary": {...}, "failed": bool, "failure_reason": str | null}`.

---

### Gap 3 — Cytoscape node/edge schema (analysis/services/graph.py vs frontend Cytoscape component)

**Pair:** `analysis/services/graph.py` (produces graph JSON) vs `frontend/src/` (consumes it with Cytoscape.js)

**Divergence scenario:** `graph.py` returns `{"nodes": [{"id": "django==6.0", "label": "django 6.0"}], "edges": [{"source": "myapp", "target": "django==6.0"}]}`. Cytoscape.js requires `{"nodes": [{"data": {"id": ..., "label": ...}}], "edges": [{"data": {"id": ..., "source": ..., "target": ...}}]}`. Both comply with AD-9 (`{nodes, edges}` JSON shape), but Cytoscape renders an empty graph.

**Gap:** AD-9 specifies the top-level shape but not the node/edge object schemas that Cytoscape.js requires.

**Fix needed:** Tighten AD-9's Rule to specify: `nodes: [{data: {id: str, label: str, version: str}}]`, `edges: [{data: {id: str, source: str, target: str}}]`.

---

### Gap 4 — SBOMJob.status ownership (sbom/ model vs tasks/sbom_pipeline.py)

**Pair:** `sbom/` (defines `SBOMJob` with a `status` field) vs `tasks/sbom_pipeline.py` (updates task progress)

**Divergence scenario:** The Celery task updates Celery's result backend (Redis) via `update_state()` but never writes to `SBOMJob.status` in PostgreSQL. The job history dashboard reads `SBOMJob.status` from PostgreSQL via the ORM and shows every job as `PENDING` forever. Alternatively: both the task AND a view update `SBOMJob.status` independently, causing race conditions on terminal state.

**Gap:** No AD specifies who owns writes to `SBOMJob.status` — the Celery task (direct ORM write) or a service function called on task state change.

**Fix needed:** New AD or Convention: "The Celery pipeline task is the sole writer of `SBOMJob.status`. It calls `sbom.services.update_job_status(job_id, status)` at each phase transition and terminal state. No view or other task writes `SBOMJob.status`."

---

### Gap 5 — Org placement on request object (users/ auth class vs DRF views)

**Pair:** `users/` (custom DRF authentication class, subclass of AbstractAPIKey auth) vs DRF views (extract org to pass to services per AD-2)

**Divergence scenario:** Auth class sets `request.auth = org_api_key_instance` (library default). View accesses `request.user.org` (assuming a custom user property). Auth class builder and view builder each make a valid, AD-compliant choice; views get `AttributeError` at runtime.

**Gap:** AD-2 says "DRF views extract org from the authenticated API key" but does not specify the interface (`request.auth.org`, `request.org`, `get_org_from_request(request)`, etc.).

**Fix needed:** Convention row: "Org is accessed in views as `request.auth.org` (set by the custom authentication class on the `OrgApiKey` instance returned as `request.auth`)."

---

### Gap 6 — Pagination envelope (DRF views vs frontend/src/api/)

**Pair:** DRF `GET /api/v1/jobs/` (paginated list) vs `frontend/src/api/` (client consuming the list)

**Divergence scenario:** DRF's default `PageNumberPagination` returns `{"count": N, "next": url, "previous": url, "results": [...]}`. Frontend builder uses the DRF docs and expects `{"items": [...], "total": N, "page": N}`. Both comply with AD-5 (all data via REST API). The frontend renders an empty job list.

**Gap:** Consistency Conventions fix the error envelope but not the pagination envelope.

**Fix needed:** Convention row: "Paginated list responses use DRF's standard `PageNumberPagination` envelope: `{count, next, previous, results}`."

---

## Summary

| Gap | Severity | Fix type |
|---|---|---|
| 1 — Manifest upload storage path | High | New convention row |
| 2 — Chord result envelope | High | New convention row |
| 3 — Cytoscape node/edge schema | High | Tighten AD-9 Rule |
| 4 — SBOMJob.status ownership | High | New AD or convention |
| 5 — Org on request object | High | New convention row |
| 6 — Pagination envelope | Medium | New convention row |
