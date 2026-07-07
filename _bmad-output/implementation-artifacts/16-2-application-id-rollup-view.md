# Story 16.2: Application-ID Rollup (Tree / Accordion View)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Second story of Epic 16 — build after 16.1** (needs the `ManagerRoute` guard, the `is_manager`
> capability, and the `has_management_access` server gate). This is the first management **view**.
> Build order: 16.1 → **16.2** → 8.26 → 16.3 → 16.4.

## Story

As a manager (or admin/global-admin),
I want a management view that groups the org's results by Application ID,
so that I can see, in one tree, every manifest and job rolled up under each application without hunting
through the flat job history.

## Acceptance Criteria

1. **Org-scoped rollup endpoint.**
   Given a manager (or admin/global-admin) of the active org, when they call a new endpoint
   (e.g. `GET /api/v1/management/application-rollup/`), then it returns the org's results **grouped by
   `application_id`** → the manifests/jobs under each → a per-result summary. Structure (illustrative):
   `[{ application_id, manifests: [{ manifest_id, filename, format, jobs: [{ job_id, status, key_counts,
   result_link }]}]}]`. The grouping key is `ManifestUpload.application_id` (`manifests/models.py:47`).
2. **Management-view gated (additive tier), server-side.**
   Given the endpoint, when called, then it is gated by `has_management_access` (Story 16.1) — role ∈
   {manager, admin} OR global-admin — returning **403** otherwise. Nav hiding is not the gate (Story 2.17).
3. **Org isolation.**
   Given a caller, when the rollup is built, then it includes **only** results belonging to the caller's
   **active org** (OrgScopedModel / AD-2) — never another org's manifests or jobs.
4. **Per-result summary + links.**
   Given each job in the tree, when rendered, then the summary shows at least its status and lightweight key
   counts (e.g. component / vulnerability / license counts already surfaced elsewhere) and a **link to the
   individual result** (the existing SBOM Results page for that job) — the rollup is navigational, not a
   re-implementation of the results tabs.
5. **Empty + partial states.**
   Given an org with no results (or an application with no completed jobs), when the view loads, then it
   renders a clear empty state (not an error/spinner-forever), and applications/manifests with only
   pending/failed jobs still appear with their status shown.
6. **Frontend tree/accordion under `ManagerRoute`.**
   Given the management nav entry (Story 16.1), when a manager opens the page, then a new page renders the
   rollup as a **tree/accordion** (Application ID → manifests → jobs), wrapped in `ManagerRoute`. A
   non-manager typing the URL is redirected (route) and 403'd (API).
7. **Tested; CI green.**
   Backend + frontend tests per the Tasks; `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Backend rollup service + endpoint (AC: #1, #3, #4)**
  - [ ] A service that, for the active org, queries `ManifestUpload` + its jobs, groups by `application_id`,
    and shapes the nested summary. Reuse the existing job/status + key-count sources the job-history and
    results pages already use (do not recompute from blobs — read the persisted DB summaries). Scope strictly
    to the active org (AD-2).
  - [ ] A view + url (`GET /api/v1/management/application-rollup/`) gated by `has_management_access`
    (Story 16.1), returning the grouped structure. Reuse the 403 envelope pattern from the admin views.
- [ ] **Task 2 — Frontend page + api client (AC: #6, #4, #5)**
  - [ ] `frontend/src/api/management.ts` (new): `getApplicationRollup()` typed to the endpoint shape.
  - [ ] A new management page (e.g. `frontend/src/pages/ManagementRollupPage.tsx`) rendering a tree/accordion
    (Application ID → manifest → job rows), each job row linking to its existing SBOM Results route, with an
    empty state. Wrap the route in `ManagerRoute` (Story 16.1) in `App.tsx`; reuse the nav entry from 16.1.
- [ ] **Task 3 — Tests (AC: #7)**
  - [ ] Backend: the rollup groups by `application_id`, includes only the active org's results (org-isolation
    test with a second org's data present), reflects status + counts, and 403s for a plain member.
  - [ ] Frontend: the page renders the tree from a mocked rollup, shows the empty state for `[]`, and links a
    job row to its results route; `ManagerRoute` redirects a non-manager.
  - [ ] `pixi run ci` green.

## Dev Notes

### The grouping key — Application ID

`application_id` is a `CharField(255)` on `ManifestUpload` (`backend/generate_sbom/manifests/models.py:47`),
carried onto jobs (`sbom/services.py:208`) and written into the SBOM as the `application:id` property
(`generation.py:106`, read back in `document.py:67`). It is the natural rollup key: multiple manifests/jobs
can share one Application ID, and this view is the first to present that grouping. Group in the query/service,
not the client, so the payload arrives shaped.

### Read the DB summaries, not the blobs

The per-result status and key counts already exist in the DB from the pipeline (the job-history dashboard and
the SBOM Results tabs read them). This view is a **rollup of existing summaries + navigation links**, so it
must not re-fetch or re-parse stored SBOM blobs (that heavier read is 16.3's job, and only for the merge).
Keep this endpoint cheap.

### Org isolation (AD-2)

Everything is scoped to the caller's active org (`OrgScopedModel`, AD-2). Add an explicit test that a second
org's manifests/jobs never appear in the rollup — the same isolation guarantee every org-scoped endpoint holds.

### Relationship to the rest of Epic 16

This is the **navigational** management view. Story 16.3 adds, per Application ID grouping shown here, a
"build consolidated SBOM" action (manager-accessible, single-App-ID). Story 16.4 adds an admin-only arbitrary
multi-select. So this tree is also the surface those merge actions will hang off — keep the Application-ID
grouping and the per-result selection affordances clean for reuse.

### Project Structure Notes

- Backend: a management service + view/url (new `management` surface or an existing app — dev's call; keep it
  gated by `has_management_access`). Reuse job/manifest querysets, no blob reads.
- Frontend: `api/management.ts`, `ManagementRollupPage.tsx`, `App.tsx` route under `ManagerRoute`, the 16.1
  nav entry, tests.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.2: Application-ID Rollup View]
- `backend/generate_sbom/manifests/models.py:47` (`application_id`), `sbom/services.py:208` (carried to jobs)
- `has_management_access` + `ManagerRoute` + `is_manager` (Story 16.1)
- Job-history / results sources for status + counts (reuse; do not recompute)
- Related: `16-1-manager-role-and-management-view-access.md`, `16-3-consolidated-sbom-by-application-id.md`,
  `13-1-global-admin-management-screen.md` (route-guard + gated-endpoint precedent)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
