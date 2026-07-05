# Story 7.2: Manual & Bulk Artifact Deletion

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to delete a job's artifacts before the 10-day TTL, and as an admin delete all my org's artifacts,
so that I can reclaim storage or remove sensitive results on demand.

## Acceptance Criteria

1. Given a job owned by my org, when I call `DELETE /api/v1/jobs/{task_id}/artifacts/`, then the shared cleanup service deletes the artifact blobs and nulls the keys; the job record is retained (FR-8.4).
2. Given a `DELETE` request for a job owned by another org, when it is processed, then the response is `404` (AD-2).
3. Given I am an org admin, when I trigger bulk-delete for the org, then all artifacts for all of the org's jobs are deleted and their keys nulled, while all job records are retained (FR-8.5).
4. Given a non-admin member, when they attempt the org-wide bulk-delete, then the action is unavailable/forbidden (FR-8.5, AD-2).
5. Given a manual or bulk deletion, when it completes, then it uses the same cleanup service function as the scheduled job (Story 7.1) — no duplicated deletion logic (AD-3).
6. Given artifacts already deleted for a job, when a manual delete is requested again, then the operation succeeds idempotently with no error.

## Tasks / Subtasks

- [ ] Task 1 — Single-job manual delete endpoint (AC: #1, #2, #5, #6)
  - [ ] Add `DELETE /api/v1/jobs/{task_id}/artifacts/` in `sbom/views.py` (DRF view)
  - [ ] Resolve the job with `SBOMJob.objects.for_org(org).get(task_id=task_id)`; `DoesNotExist` → `404` (never `403` on the API surface, AD-2)
  - [ ] Call the shared `delete_job_artifacts(job)` service from Story 7.1 — do NOT reimplement deletion (AD-3)
  - [ ] Return `204 No Content` (or `200` with a small envelope) on success; retain the job record
  - [ ] Idempotent: deleting an already-cleaned job (null `result_key`) still returns success (AC #6)
- [ ] Task 2 — Org-wide bulk delete (AC: #3, #4, #5)
  - [ ] Add an admin-only endpoint (e.g. `POST /api/v1/orgs/artifacts/purge/` or `DELETE /api/v1/jobs/artifacts/`) that iterates `SBOMJob.objects.for_org(org).filter(result_key__isnull=False)` and calls `delete_job_artifacts(job)` for each
  - [ ] Enforce admin role: read the caller's `OrgMembership.role` for `request.auth.org`; non-admins receive `403` (FR-8.5). API cross-org access remains `404` per AD-2
  - [ ] Add a bulk-delete service `delete_org_artifacts(org: Org) -> int` in `sbom/services.py` returning count cleaned, itself calling the per-job primitive
- [ ] Task 3 — Web UI wiring (AC: #1, #3, #4)
  - [ ] Results page / job row: a "Delete artifacts" control that calls the manual-delete endpoint via `frontend/src/api/jobs.ts` (no direct fetch in components, AD-5)
  - [ ] Admin-only "Delete all org artifacts" control on the appropriate settings/keys page; hidden/disabled for non-admin members (mirrors admin-gating pattern from Epic 2 stories)
- [ ] Task 4 — Tests (AC: #1–#6)
  - [ ] Manual delete happy path: blobs gone, keys nulled, job row retained
  - [ ] Cross-org manual delete → `404`
  - [ ] Bulk delete as admin cleans all org jobs; job rows retained
  - [ ] Bulk delete as non-admin → `403`
  - [ ] Idempotent re-delete → success, no storage error
  - [ ] Assert the endpoints call the shared `delete_job_artifacts` (no duplicated logic)

## Dev Notes

### Reuse the Story 7.1 primitive (AD-3) — do not duplicate

The deletion mechanics (delete `sbom-results/{org_id}/{task_id}/` prefix, null `result_key` + related `AnalysisReport.artifact_key`, never delete the job row) live in `delete_job_artifacts(job)` from Story 7.1. Both endpoints in this story are thin wrappers:

- Manual: resolve one org-scoped job → call the primitive.
- Bulk: `delete_org_artifacts(org)` loops the org's jobs with a non-null `result_key` → calls the primitive per job.

If Story 7.1 is not yet implemented, that service function is the prerequisite — build it first (its Task 1) before wiring these views.

### Org scoping & error semantics (AD-2)

- Job lookup uses `SBOMJob.objects.for_org(org).get(...)`; a job owned by another org raises `DoesNotExist`, surfaced as `404` — existence is never disclosed to another org on the API surface.
- Admin gating (bulk delete) returns `403` for authenticated non-admin members of the *same* org — this is an authorization signal within the org, distinct from the cross-org `404`. Read role from `OrgMembership` for `request.auth.org`.

### Idempotency

`delete_job_artifacts` short-circuits when `result_key` is null (Story 7.1), so repeated manual deletes and overlap with the nightly Beat sweep are safe.

### Storage / retention invariants

- Only blobs + keys are removed; `SBOMJob` and `AnalysisReport` rows persist with their metadata (FR-8.4, FR-8.5). Story 7.3 renders the "artifacts unavailable" state these deletions produce.

### Dependency / sequencing notes

- Depends on Story 7.1 (`delete_job_artifacts` service).
- Depends on `SBOMJob` model + org membership/role model (Epic 2, Epic 3).
- The jobs list endpoint (`GET /api/v1/sbom/jobs/`) is Epic 6; this story adds the `DELETE .../artifacts/` sibling under the same `sbom/views.py`.

### Project Structure Notes

- Endpoints in `sbom/views.py` (DRF viewsets only); mutation logic in `sbom/services.py`; role read via a selector on `users/`.
- Frontend calls via `frontend/src/api/jobs.ts`; admin-gated control follows the Epic 2 admin-visibility pattern.
- No new models or migrations.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.2: Manual & Bulk Artifact Deletion]
- [Source: _bmad-output/implementation-artifacts/7-1-scheduled-artifact-expiry-and-cleanup.md#Task 1 — Shared cleanup service function]
- [Source: solution-design.md#4.5 Celery Beat — artifact cleanup]
- [Source: solution-design.md#6.1 Storage paths]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel (404 cross-org)]
- [Source: ARCHITECTURE-SPINE.md#AD-3 — Service layer purity (no duplicated deletion logic)]
- [Source: ARCHITECTURE-SPINE.md#AD-6 — Storage triad]
- [Source: prd.md#FR-8.4, FR-8.5]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

### Completion Notes List

- Reused Story 7.1's `delete_job_artifacts(job)` (AD-3, no duplicated deletion logic); added a thin `delete_artifacts_for_jobs(jobs)` bulk primitive that loops it.
- `DELETE /api/v1/sbom/jobs/{task_id}/artifacts/` for a single job (org member; 404 cross-org/unknown via `get_job`; idempotent).
- `POST /api/v1/sbom/jobs/artifacts/bulk-delete/`: `{"all": true}` is admin-only (`get_admin_org` → 403 for members) and purges the whole org; `{"task_ids": [...]}` purges the named org jobs (frontend bulk selection). Invalid UUID strings are skipped.
- Endpoint path uses the repo's `sbom/` prefix (`/api/v1/sbom/jobs/...`) rather than the AC's illustrative `/api/v1/jobs/...`, matching every other job route.
- Frontend: per-row delete icon (`DeleteActionIcon` from the 12.2 vocabulary), checkbox selection + "Delete selected", admin-only "Delete all artifacts", all behind a confirmation dialog; the list refreshes after a delete.

### File List

- backend/generate_sbom/sbom/services.py (add `delete_artifacts_for_jobs`)
- backend/generate_sbom/sbom/views.py (add `JobArtifactsView`, `BulkDeleteArtifactsView`)
- backend/generate_sbom/sbom/urls.py (wire the two routes)
- backend/tests/unit/test_artifact_deletion.py (new)
- frontend/src/api/jobs.ts (`deleteJobArtifacts`, `bulkDeleteArtifacts`)
- frontend/src/pages/HistoryPage.tsx (delete UI)
- frontend/src/pages/HistoryPage.test.tsx (delete tests + auth mock)
