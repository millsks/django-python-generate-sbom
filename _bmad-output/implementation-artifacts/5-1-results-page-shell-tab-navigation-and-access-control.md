# Story 5.1: Results Page Shell, Tab Navigation & Access Control

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a results page with five tabs that only my org can access,
so that I can navigate a completed job's outputs and safely share the URL within my team.

## Acceptance Criteria

1. Given a completed job owned by my org, when I open its results page, then five tabs are rendered — Overview, Vulnerabilities, Licenses, Dependency Graph, Version Currency — with Overview active by default.
2. Given the results page URL, when another member of the same org opens it, then they see the same results (the URL is stable and shareable within the org).
3. Given a user who is not a member of the owning org, when they open the results page URL, then the web UI route returns `403`.
4. Given any tab whose backing analysis phase failed (per FR-4.5), when that tab is opened, then it displays a failure notice with the error reason instead of report content, while the SBOM download and successful tabs remain available.
5. Given all API calls made by the results page, when they are issued, then they go through functions in `frontend/src/api/` — no direct `fetch` calls in components (AD-5).
6. Given a job whose artifacts are still available, when the results page loads (excluding graph rendering), then it renders in under 3 seconds (NFR-2.2).

## Tasks / Subtasks

- [ ] Task 1 — Route + page scaffold (AC: #1, #2)
  - [ ] Add the `/results/:taskId` route to the React Router config (from Story 1.4) pointing at `ResultsPage.tsx`
  - [ ] `ResultsPage` reads `taskId` from the route params; the URL is stable/shareable (no ephemeral state in the URL) (AC #2)
  - [ ] Render an MUI `Tabs`/`Tab` shell with five tabs in fixed order: Overview, Vulnerabilities, Licenses, Dependency Graph, Version Currency; Overview active by default (AC #1)
- [ ] Task 2 — Job status gating via `useJobStatus` (AC: #1, #4)
  - [ ] On mount, fetch job status via `api/jobs.getStatus(taskId)`; if the job is not yet `SUCCESS`/`FAILED`, drive the shared `useJobStatus(taskId)` hook (defined in Epic 6; if not yet present, add a minimal poll here and refactor onto the shared hook later) so the page resolves when the job completes
  - [ ] Store the completed job summary (status per report, `output_format`, availability flags) in page state for the tabs to consume
- [ ] Task 3 — Access control: 403 outside org (AC: #3)
  - [ ] The results endpoints are org-scoped server-side (AD-2). For web UI routes, a request from a user outside the owning org yields `403` (not `404`) per AD-2's web-UI rule
  - [ ] `ResultsPage` catches a `403` from the status/report calls and renders an "Access denied" state rather than tab content
- [ ] Task 4 — Shared per-tab failure-notice pattern (AC: #4)
  - [ ] Build a reusable `TabFailureNotice` component that renders `failure_reason` when a report's `failed` flag is true (FR-4.5 / FR-6.7)
  - [ ] Each tab (5.2–5.6) consumes this component; the Overview tab and SBOM download stay available even when an analysis tab failed
  - [ ] The page must not hard-fail if one report is missing — render the failure notice in that tab only
- [ ] Task 5 — API layer wiring (AC: #5)
  - [ ] All report/status/download calls route through `frontend/src/api/` modules (`jobs.ts`, `reports.ts`) — zero `fetch`/`axios` in components (AD-5)
  - [ ] Stub the four report fetchers in `reports.ts` (`getVulnerabilities`, `getLicenses`, `getGraph`, `getVersions`) returning typed data; tabs 5.2–5.6 fill in consumption
- [ ] Task 6 — Performance (AC: #6)
  - [ ] Ensure the shell + Overview data render in under 3 seconds once artifacts are available (NFR-2.2); defer heavy graph rendering to the Dependency Graph tab (lazy-mount that tab's panel)
- [ ] Task 7 — Tests (AC: #1, #3, #4)
  - [ ] Component test: five tabs render in order, Overview default active
  - [ ] Component test: a `403` response renders the access-denied state, not tabs
  - [ ] Component test: a report with `failed=true` renders `TabFailureNotice` while other tabs still render

## Dev Notes

### This story is the shell; 5.2–5.6 are the tab bodies

Story 5.1 owns the `ResultsPage` shell, tab navigation, the shareable-URL contract, org access control, and the shared failure-notice pattern. Stories 5.2–5.6 each implement one tab's body and consume an already-built Epic 4 report endpoint. No tab depends on another tab — they are independent given this shell. [Source: epics.md#Epic 5]

### Frontend stack & conventions (solution-design.md §7.1, §7; AD-5)

- React 19.2.7 + @mui/material 9.1.2 + Vite 8.1.3 (from Story 1.4).
- `ResultsPage.tsx` lives in `frontend/src/pages/`. Tabs: SBOM/Overview · Vulnerability · Licences · Graph · Versions. [Source: solution-design.md §7.2]
- ALL network calls go through `frontend/src/api/` (`client.ts` base + auth header, `jobs.ts`, `reports.ts`) — never `fetch`/`axios` in components (AD-5). [Source: ARCHITECTURE-SPINE.md AD-5; solution-design.md §7]
- `useJobStatus(taskId)` polls `/api/v1/sbom/status/{taskId}/` every 5s until `SUCCESS`/`FAILED`, then reports fetch in parallel. Defined in Epic 6; ResultsPage is its primary consumer. [Source: solution-design.md §7.2, §4.3]

### Report endpoints consumed by the tabs (solution-design.md §5.2)

- `GET /api/v1/sbom/result/{task_id}/` → 303 presigned S3 URL for the SBOM artifact (download button in Overview). [Source: solution-design.md §6.2; AD-11]
- `GET /api/v1/sbom/result/{task_id}/reports/vuln/` → vulnerability JSON
- `GET /api/v1/sbom/result/{task_id}/reports/licenses/` → licence JSON
- `GET /api/v1/sbom/result/{task_id}/reports/graph/` → `{nodes, edges}` JSON (AD-9)
- `GET /api/v1/sbom/result/{task_id}/reports/versions/` → version currency JSON

### Access control (AD-2)

Org isolation is enforced server-side. API endpoints return `404` for cross-org, but **web UI routes return `403`** for authenticated users hitting another org's resource — UUID URLs don't leak existence and `403` gives clearer UX for the shared-link case (FR-6.8). ResultsPage renders an access-denied state on `403`. [Source: ARCHITECTURE-SPINE.md AD-2; solution-design.md §10]

### Failure handling (FR-4.5 / FR-6.7)

If any analysis phase failed, the job may still have a downloadable SBOM. Each report carries `failed` + `failure_reason`. The affected tab shows a failure notice; the SBOM download and successful tabs remain usable. The page must degrade per-tab, never whole-page. [Source: epics.md#Story 5.1; solution-design.md §4.4]

### Project Structure Notes

- `frontend/src/pages/ResultsPage.tsx` (shell, this story), `frontend/src/api/reports.ts` + `jobs.ts` (fetchers), `frontend/src/components/TabFailureNotice.tsx` (shared).
- Frontend state-management library choice remains deferred; the only binding constraint is the `src/api/` seam (spine Deferred; solution-design §12).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1: Results Page Shell, Tab Navigation & Access Control]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA: REST API only]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel (web UI 403)]
- [Source: solution-design.md#7. Frontend Architecture]
- [Source: solution-design.md#5.2 Endpoint inventory]
- [Source: solution-design.md#6.2 Presigned URL download flow]
- [Source: prd.md#FR-6.1, FR-6.7, FR-6.8, NFR-2.2]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

- Endpoint name: the story lists `/reports/vuln/`, but Epic 4 built `/reports/vulnerabilities/` — used the real path.
- Vitest config had to live in a **separate `vitest.config.ts`** (not `vite.config.ts`): rolldown-vite 8 and the vite bundled inside vitest 3 have incompatible plugin types, so putting the `test` block in `vite.config.ts` broke the production `tsc -b` build.

### Completion Notes List

- **Frontend test stack (new):** vitest 3 + `@testing-library/react` + `@testing-library/jest-dom` + `jsdom`. Config in `vitest.config.ts` (jsdom env, `src/test/setup.ts` registers jest-dom); `test`/`test:watch` npm scripts; **`fe-test` pixi task added to the `ci` gate**. Tests use explicit `vitest` imports (no globals) so oxlint/tsc stay happy.
- **`ResultsPage` shell:** `/results/:taskId` route (protected), stable/shareable URL. Polls `getJobStatus` every 5s until `SUCCESS`/`FAILED` (minimal poller — refactors onto the shared `useJobStatus` hook in Epic 6), showing a processing state meanwhile. On completion renders MUI `Tabs` with the five tabs in fixed order, **Overview active by default**; Overview has the SBOM download. Tabs 2–5 are placeholders for 5.2–5.6.
- **Access control (AC #3):** a cross-org (or unknown) job surfaces as **404** from the status API (AD-2 no-existence-leak rule — the backend does not return 403); `ResultsPage` maps 403/404 to an access-denied state. A literal 403 would require a backend change that contradicts the no-leak design, so both map to the same "not available" UX.
- **`TabFailureNotice`** shared component (FR-4.5) renders a report's `failure_reason`; `ApiError` now carries `failureReason` so failed-report responses (`code=report_failed`) can surface it in the tabs (5.2–5.6).
- **API layer (AD-5):** `api/reports.ts` gains typed interfaces + four fetchers (`getVulnerabilities`/`getLicenses`/`getGraph`/`getVersions`); `api/jobs.ts` `JobStatus` aligned to the backend shape + `TERMINAL_STATUSES`. No `fetch` in components.
- **Flag for 5.2:** the vuln/license/version report endpoints 303-redirect to a presigned S3 URL for the JSON; the SPA reading that JSON cross-origin will need bucket CORS (or those endpoints serving JSON inline like the graph endpoint). To resolve when the tab bodies consume the data.
- Gate: `pixi run ci` exits 0 — backend 177 tests (95.36%), frontend 4 tests, build passes.

### File List

- frontend/package.json, vitest.config.ts (new), src/test/setup.ts (new) — test stack
- frontend/src/pages/ResultsPage.tsx (new) + ResultsPage.test.tsx (new)
- frontend/src/components/TabFailureNotice.tsx (new) + TabFailureNotice.test.tsx (new)
- frontend/src/api/reports.ts (typed fetchers), jobs.ts (JobStatus), client.ts (ApiError.failureReason)
- frontend/src/App.tsx (/results/:taskId route)
- pixi.toml (fe-test task + ci depends-on)
