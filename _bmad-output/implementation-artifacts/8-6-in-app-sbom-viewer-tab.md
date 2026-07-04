# Story 8.6: In-App SBOM Viewer Tab

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to read the SBOM in the UI in a tab next to Overview,
so that I can inspect it without downloading and opening a file.

## Acceptance Criteria

1. Given a completed job, when the results page loads, then an "SBOM" tab appears immediately to the right of Overview (before Vulnerabilities).
2. Given the SBOM tab, when it opens, then it shows a structured component table (at minimum name, version, type, license; and the direct/transitive column once 8.3/8.4 land) parsed from the stored SBOM, regardless of output format (`cdx-json`, `cdx-xml`, `spdx-2.3`).
3. Given the SBOM tab, when I toggle to the raw view, then it shows the exact SBOM document pretty-printed and readable (syntax-highlighted / collapsible for JSON), matching what the download would produce.
4. Given the SBOM content is served to the SPA, when the tab fetches it, then it comes from an inline content endpoint (a JSON payload with a normalized component list + the raw document text) via `src/api/` — not the `303`-presigned download flow — mirroring the inline report-endpoint pattern (AD-5).
5. Given a job whose artifacts were never produced or have expired/been deleted, when the SBOM tab renders, then it shows an appropriate unavailable/failure notice rather than erroring.
6. Given a cross-org or unknown job, when the SBOM content endpoint is called, then it returns `404` (AD-2), matching the other job endpoints (no existence leak).
7. Given the component table, when it has many rows, then it is scannable (sortable by at least name; the table scrolls within its own container without breaking the page layout).

## Tasks / Subtasks

- [ ] Task 1 — SBOM content endpoint (AC: #2, #4, #5, #6)
  - [ ] Add `GET /api/v1/sbom/document/{task_id}/` (sbom app) returning JSON: `{ "format": <output_format>, "components": [{name, version, type, license, relationship?}], "raw": "<pretty document text>" }`
  - [ ] Load the stored artifact from `default_storage` by the job's `result_key`; org-scope via `get_job` (404 on cross-org/unknown — AD-2)
  - [ ] Parse the stored SBOM into the normalized component list on the server (reuse `cyclonedx-python-lib` / `lib4sbom`), so the SPA is format-agnostic
  - [ ] `404` with a clear code when `result_key` is null / artifact missing (never produced, expired, or deleted — aligns with Epic 7)
  - [ ] Pretty-print `raw` (indented JSON / formatted XML) so the raw view is readable
- [ ] Task 2 — Frontend API (AC: #4)
  - [ ] Add `getSbomDocument(taskId)` to `frontend/src/api/reports.ts` (or `sbom.ts`) with typed `SbomDocument` (`format`, `components`, `raw`) — the only place the fetch lives (AD-5)
- [ ] Task 3 — SBOM viewer tab (AC: #1, #2, #3, #7)
  - [ ] Add an `SbomTab` component and insert it in `ResultsPage` as the second tab (index 1), shifting the analysis tabs right
  - [ ] Structured table view: MUI table (name, version, type, license, direct/transitive when present), sortable by name, scroll-contained
  - [ ] Raw toggle: a segmented control / tabs (`Components` | `Raw`) rendering the pretty-printed `raw` in a monospace, scrollable, collapsible block
  - [ ] Failure/empty states: unavailable notice (reuse `TabFailureNotice` pattern) when the endpoint 404s or the artifact is gone
- [ ] Task 4 — Tests
  - [ ] Backend: endpoint returns normalized components + raw for a cdx-json job; parses cdx-xml and spdx too; `404` on cross-org and on missing artifact
  - [ ] Frontend: table renders parsed components; toggle switches to raw; unavailable state on `report_failed`/404
  - [ ] `pixi run ci` exits 0 with ≥90% backend coverage on the new endpoint

## Dev Notes

### Endpoint pattern (AD-5, AD-11)

The report tabs (Vulnerabilities/Licenses/Versions) fetch their data **inline as JSON** via `_JsonReportView`-style endpoints, not the `303`-to-presigned flow used for the SBOM/graph *downloads*. The SBOM viewer follows the same inline pattern: a new `GET /sbom/document/{task_id}/` returns a JSON envelope the SPA renders directly, avoiding S3/MinIO CORS for in-page viewing. The existing `ResultJobView` (`/sbom/result/...`, 303 download) stays as-is for the download button. [Source: backend/generate_sbom/analysis/views.py, backend/generate_sbom/sbom/views.py]

### Server-side normalization

Parse the stored SBOM on the server into a common component list so the frontend never needs a CycloneDX/SPDX/JSON/XML parser. The generators already depend on `cyclonedx-python-lib` (CycloneDX) and `lib4sbom` (SPDX); reuse them (or a light targeted parse) to extract name/version/type/license and, once 8.3/8.4 land, the direct/transitive relationship. The `raw` field carries the exact document text (pretty-printed) for the raw toggle. [Source: backend/generate_sbom/sbom/services.py — generate_sbom_document]

### Tab placement (FR-6.1 / Story 5.1)

`ResultsPage` currently renders five tabs (Overview, Vulnerabilities, Licenses, Dependency Graph, Version Currency) from `TAB_LABELS`. Insert "SBOM" at index 1 (right of Overview); the panels are index-driven, so shift the analysis panels accordingly and keep `OverviewTab`'s in-app links pointing at the correct indices. [Source: frontend/src/pages/ResultsPage.tsx]

### Direct/transitive column

The `relationship` column is optional in this story — it renders when present in the normalized payload (populated by 8.3/8.4) and is simply omitted/blank otherwise, so 8.6 can ship independently of the direct/transitive thread.

### Expiry alignment (Epic 7)

When artifacts are expired/deleted (Epic 7), `result_key` is nulled; the endpoint's missing-artifact `404` is the same path the tab uses to show its unavailable notice — no special-casing needed beyond a clear code.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.6: In-App SBOM Viewer Tab]
- [Source: prd.md#FR-6.1 — Results page tabs]
- [Source: frontend/src/pages/ResultsPage.tsx]
- [Source: frontend/src/api/reports.ts]
- [Source: backend/generate_sbom/analysis/views.py — inline JSON report views]
- [Source: backend/generate_sbom/sbom/views.py — ResultJobView 303 download]
- [Source: ARCHITECTURE-SPINE.md#AD-2, AD-5, AD-11]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
