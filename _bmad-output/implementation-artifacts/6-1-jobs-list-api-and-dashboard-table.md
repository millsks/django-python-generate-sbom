# Story 6.1: Jobs List API & Dashboard Table

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a dashboard listing all my org's SBOM jobs,
so that I can review past and current jobs and jump to their results.

## Acceptance Criteria

1. Given `GET /api/v1/sbom/jobs/` with an org-scoped credential, when the request is processed, then it returns the org's jobs most-recent-first, each with submitted time, manifest filename, manifest format, output format, and status; jobs from other orgs are excluded.
2. Given the jobs list endpoint, when results are returned, then they are paginated at 25 per page using the standard envelope `{"count", "next", "previous", "results"}`.
3. Given the jobs list endpoint, when I pass a status filter (`All`/`In Progress`/`Completed`/`Failed`) and/or a manifest-format filter, then only matching jobs are returned.
4. Given the dashboard table in the web UI, when it renders, then it shows columns for submitted time, manifest filename, manifest format, output format, status (with a visual indicator), and a link to results.
5. Given a job in `FAILED` state, when it appears in the list, then its row displays a failure reason summary.
6. Given the dashboard filter controls, when I select a status or manifest-format filter, then the table updates to show only matching jobs, driven by the API filter parameters.
7. Given a completed job row, when I click its results link, then I navigate to that job's five-tab results page.

## Tasks / Subtasks

- [ ] Task 1 — Jobs list selector (AC: #1, #3)
  - [ ] Add `sbom/selectors.py` function `get_jobs(org, *, status_filter=None, format_filter=None)` returning `SBOMJob.objects.for_org(org)` ordered by `-created_at` (AD-2; org is first positional arg)
  - [ ] Map the UI status filter values to `SBOMJob.status`: `In Progress` → `status__in=['PENDING','PROGRESS']`; `Completed` → `SUCCESS`; `Failed` → `FAILED`; `All` → no status filter
  - [ ] Apply `manifest__detected_format` filter when `format_filter` is supplied
  - [ ] Keep the selector read-only (no mutations) per file-roles convention
- [ ] Task 2 — Jobs list serializer (AC: #1, #4, #5)
  - [ ] Serialize submitted time (`created_at`, ISO 8601 UTC), manifest filename (`manifest.original_filename`), manifest format (`manifest.detected_format`), output format, status, and `failure_reason` (null unless FAILED)
  - [ ] Include `task_id` so the frontend can build the results link
- [ ] Task 3 — Jobs list endpoint (AC: #1, #2, #3)
  - [ ] Add DRF view for `GET /api/v1/sbom/jobs/` in `sbom/views.py`; read `org = request.auth.org` and pass to the selector (AD-2)
  - [ ] Use `PageNumberPagination` with `page_size=25`, `max_page_size=100` via `?page_size=`; envelope `{"count","next","previous","results"}`
  - [ ] Accept query params for status filter and manifest-format filter
  - [ ] Wire the URL under the `/api/v1/` prefix
- [ ] Task 4 — Frontend API module (AC: #1, #2, #3, #6)
  - [ ] Add `listJobs({ page, status, format })` to `frontend/src/api/jobs.ts` — the only place the `/sbom/jobs/` fetch lives (AD-5; no fetch in components)
  - [ ] Return the typed pagination envelope
- [ ] Task 5 — HistoryPage dashboard table (AC: #4, #5, #6, #7)
  - [ ] Build `frontend/src/pages/HistoryPage.tsx` (route `/history`) rendering an MUI table with the six columns
  - [ ] Render status with a visual indicator (reuse/create `JobStatusBadge.tsx`)
  - [ ] Show the failure reason summary on `FAILED` rows (AC #5)
  - [ ] Add status and manifest-format filter controls that re-query via `listJobs` (AC #6)
  - [ ] Add pagination controls (25/page) reflecting the API envelope `count`/`next`/`previous`
  - [ ] Each row's results link routes to `/results/:taskId` (AC #7)
- [ ] Task 6 — Tests
  - [ ] Unit: selector returns only the org's jobs, most-recent-first; status/format filters map correctly; cross-org jobs excluded
  - [ ] Unit/integration: endpoint returns the pagination envelope with `page_size=25`; filter params honored; `404`/empty for other org
  - [ ] Confirm `pixi run ci` exits 0 with ≥90% coverage on the new selector/view

## Dev Notes

### Endpoint & pagination contract (solution-design.md §5.2, §5.3)

`GET /api/v1/sbom/jobs/` returns org jobs paginated. Standard envelope:

```json
{
  "count": 47,
  "next": "/api/v1/sbom/jobs/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

`page_size` default 25, max 100 via `?page_size=`. Use DRF `PageNumberPagination`. [Source: solution-design.md#5.3 Standard response shapes]

### Org scoping (AD-2)

All queries go through `SBOMJob.objects.for_org(org)`. `org = request.auth.org` in the view; passed as the first positional arg to the selector. Cross-org jobs are simply absent from the queryset — no separate authorization branch needed for the list endpoint. [Source: ARCHITECTURE-SPINE.md#AD-2]

### Status filter mapping

The UI exposes `All / In Progress / Completed / Failed`; `SBOMJob.status` values are `PENDING | PROGRESS | SUCCESS | FAILED`. Map `In Progress` to `['PENDING','PROGRESS']`, `Completed` to `SUCCESS`, `Failed` to `FAILED`. Manifest-format filter targets `manifest.detected_format` (`requirements | pyproject | pixi_lock | pixi_toml | conda`). [Source: solution-design.md#3.2, #3.3]

### Frontend (AD-5; solution-design.md §7.2)

`HistoryPage.tsx` at route `/history` lists past jobs and links each to `ResultsPage` (`/results/:taskId`). All network access via `frontend/src/api/jobs.ts` — no direct `fetch` in the component (AD-5). This story renders **static** status per row; live auto-refresh of in-progress rows is Story 6.2. [Source: solution-design.md#7.2 Page structure]

### Dependency / sequencing notes

- Depends on `SBOMJob`, `ManifestUpload`, and `OrgScopedModel` existing (Epic 3 Stories 3.1–3.2, Epic 1 Story 1.3).
- Depends on the API auth layer and `request.auth.org` (Epic 2 Story 2.4).
- Independent of Story 6.2 — the table works with static status; 6.2 layers polling on top.
- `ResultsPage` (`/results/:taskId`) is built in Epic 5; the results link target may not exist yet when this story lands — the link is still correct and becomes live once Epic 5 is done.

### Project Structure Notes

- Backend: `sbom/views.py` (jobs list view), `sbom/selectors.py` (`get_jobs`), `sbom/serializers.py` (jobs list serializer), URL under `/api/v1/`.
- Frontend: `frontend/src/pages/HistoryPage.tsx`, `frontend/src/api/jobs.ts`, `frontend/src/components/JobStatusBadge.tsx`.
- Selectors are read-only; keep filtering logic there, not in the view (file-roles convention).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.1: Jobs List API & Dashboard Table]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA: REST API only]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Pagination]
- [Source: solution-design.md#5.2 Endpoint inventory]
- [Source: solution-design.md#5.3 Standard response shapes]
- [Source: solution-design.md#7.2 Page structure]
- [Source: prd.md#FR-7.1, FR-7.3, FR-7.4, FR-7.5]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- **Backend:** `selectors.get_jobs(org, *, status_filter, format_filter)` — `for_org(org)` (AD-2), `-created_at`, with the UI status-label mapping (`In Progress`→PENDING/PROGRESS, `Completed`→SUCCESS, `Failed`→FAILED, `All`/None→none) and `manifest__detected_format` filter. `JobListSerializer` (ModelSerializer) exposes task_id, created_at, manifest_filename, manifest_format, output_format, status, failure_reason. `JobsListView` (`ListAPIView`) with `JobsPagination` (25/page, up to 100 via `?page_size=`); org from `get_request_org`, empty queryset when no org. Route `GET /api/v1/sbom/jobs/`.
- **Frontend:** `listJobs({page, status, format})` in `api/jobs.ts` (typed `Paginated<JobListItem>` envelope; drops `status=All`). `JobStatusBadge` maps status → colored Chip (In Progress/Completed/Failed). `HistoryPage` (`/history`): MUI table with the six columns, status + manifest-format filter controls (reset to page 1 on change), MUI `Pagination` reflecting `count`, failure-reason text on FAILED rows, and a "View" link per row to `/results/:taskId`. Static status only (live polling is 6.2).
- **Tests:** backend — selector org-scoping/order/filters + endpoint pagination-envelope/serialization/filters/cross-org exclusion; frontend — row columns + results link, failure reason on FAILED, status-filter re-query resets page, empty state.
- **Still pending (flagged earlier):** the upload form still posts to `/manifests/upload/`; wiring it to `/sbom/generate/` (so a UI submission appears in this dashboard) remains a small follow-up — I'll do it after Epic 6.
- Gate: `pixi run ci` exits 0 — backend 183 tests (95.28%), frontend 26 tests.

### File List

- backend/generate_sbom/sbom/selectors.py (get_jobs), serializers.py (JobListSerializer), views.py (JobsPagination, JobsListView), urls.py (sbom/jobs/)
- backend/tests/unit/test_jobs_list.py (new)
- frontend/src/api/jobs.ts (listJobs + types), components/JobStatusBadge.tsx (new), pages/HistoryPage.tsx (new) + HistoryPage.test.tsx (new)
- frontend/src/App.tsx (/history route)
