# Story 3.2: Job Submission, Concurrency Gate & Status API

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to submit a validated manifest and immediately receive a task ID I can poll,
so that I get a fast response and can track progress asynchronously.

## Acceptance Criteria

1. Given a validated manifest and an org below its concurrency limit, when I `POST /api/v1/sbom/generate/` with an optional `output_format`, then a `SBOMJob` is created with `status="PENDING"`, `artifacts_expire_at` is left null until completion, the pipeline task is dispatched via `delay_on_commit()`, and the response is `202` with `{task_id, status_url, estimated_seconds}` (FR-3.5, AD-10, AD-12).
2. Given the `output_format` parameter, when it is `cdx-json` (default), `cdx-xml`, or `spdx-2.3`, then the value is accepted and stored on the job; any other value returns `400` with a clear error (FR-3.6).
3. Given the submitting org already has `SBOM_MAX_CONCURRENT_JOBS_PER_ORG` jobs in `PENDING` or `PROGRESS`, when I submit another job, then the concurrency gate in `manifests/views.py` returns `429` with a `Retry-After` header and no job is created (FR-3.5, AD-7, NFR-4.1).
4. Given the concurrency count check, when it executes, then it uses `SBOMJob.objects.for_org(org).filter(status__in=['PENDING', 'PROGRESS']).count()` before dispatch (AD-7).
5. Given a job owned by Org A, when the same user acting under Org B calls `GET /api/v1/sbom/status/{task_id}/`, then the response is `404` — the job is invisible outside its owning org (FR-3.7, AD-2).
6. Given an active job, when I `GET /api/v1/sbom/status/{task_id}/`, then the response includes `status` (`PENDING`/`PROGRESS`/`SUCCESS`/`FAILURE`), `progress` (0–100), `current_phase` name, and — on success — a `result_url` (FR-4.7).
7. Given the `estimated_seconds` value, when a job is submitted, then it is computed from manifest format and file size and returned in the `202` response (FR-3.5).
8. Given `SBOMJob.status`, when any code other than the initial `PENDING` set in `manifests/views.py` attempts to write it from a view, then that is a violation — status is mutated only by Celery task code via a dedicated `sbom/services.py` function (AD-12).

## Tasks / Subtasks

- [ ] Task 1 — `SBOMJob` model (AC: #1, #2, #6)
  - [ ] `sbom/models.py` `SBOMJob(OrgScopedModel)` with fields per Dev Notes (task_id UUID PK, manifest FK, user FK, status, progress, current_step, output_format, result_key, summary_stats, created_at, completed_at, artifacts_expire_at, failure_reason)
  - [ ] Generate migration
- [ ] Task 2 — Generate endpoint + concurrency gate (AC: #1, #3, #4)
  - [ ] `POST /api/v1/sbom/generate/` lives in `manifests/views.py` (AD-7 — this view owns record creation AND the gate in one transaction)
  - [ ] Run the concurrency count (AC #4 exact query) BEFORE creating the job; if `>=` limit → `429` + `Retry-After` header, no job created
  - [ ] Create `ManifestUpload` (reuse Story 3.1 upload service) + `SBOMJob(status='PENDING')` in the same transaction
  - [ ] Dispatch the pipeline task with `delay_on_commit()` (AD-10) — never `.delay()`
  - [ ] Return `202` with `{task_id, status_url, estimated_seconds}`
- [ ] Task 3 — output_format validation (AC: #2)
  - [ ] Accept `cdx-json` (default), `cdx-xml`, `spdx-2.3`; reject others with `400` + error envelope
  - [ ] Map to the internal serializer identifiers used in Story 3.4
- [ ] Task 4 — estimated_seconds heuristic (AC: #7)
  - [ ] Compute a rough estimate from `detected_format` + file size; return in the 202 body
- [ ] Task 5 — Status endpoint (AC: #5, #6)
  - [ ] `GET /api/v1/sbom/status/{task_id}/` reads via `SBOMJob.objects.for_org(org).get(task_id=...)` → `404` on cross-org/nonexistent (AD-2)
  - [ ] Return `status`, `progress`, `current_phase` (from `current_step`), and `result_url` on success (per solution-design §5.3 status shape)
- [ ] Task 6 — Status-write service seam (AC: #8)
  - [ ] Add `sbom/services.py update_job_status(task_id, status, progress, current_step, failure_reason)` and `finalize_job(task_id, result_key, summary_stats)` — the ONLY writers of `status` (used by task code in Stories 3.4/3.5)
  - [ ] The generate view sets the initial `PENDING` only; document the AD-12 rule in the module docstring
- [ ] Task 7 — Tests (AC: all)
  - [ ] Unit: gate returns 429 at limit with Retry-After; below limit creates job + PENDING
  - [ ] Unit: invalid output_format → 400; valid values stored
  - [ ] Unit: cross-org status poll → 404; valid poll returns the status shape
  - [ ] Unit: dispatch uses `delay_on_commit()` (assert via mocked task)
  - [ ] ≥90% coverage; `pixi run ci` exits 0

## Dev Notes

### `SBOMJob` model (solution-design.md §3.3)

```python
class SBOMJob(OrgScopedModel):
    task_id: UUID          # PK; also Celery task ID
    manifest: FK(ManifestUpload)
    user: FK(User)
    status: str            # 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILED'
    progress: int          # 0–100
    current_step: str      # phase name; displayed in UI
    output_format: str     # 'cyclonedx-json' | 'cyclonedx-xml' | 'spdx-json'
    result_key: str | None # sbom-results/{org_id}/{task_id}/{filename}.{ext}
    summary_stats: dict
    created_at: datetime
    completed_at: datetime | None
    artifacts_expire_at: datetime | None
    failure_reason: str | None
```

Note: PRD/epics use API-facing `output_format` values `cdx-json|cdx-xml|spdx-2.3`; the model stores the internal serializer id (`cyclonedx-json|cyclonedx-xml|spdx-json`). Map at the view boundary.

### Concurrency gate (AD-7; solution-design.md §5.4) — exact code

```python
active = SBOMJob.objects.for_org(org).filter(
    status__in=['PENDING', 'PROGRESS']
).count()
if active >= settings.SBOM_MAX_CONCURRENT_JOBS_PER_ORG:   # default 5
    return Response(
        {"error": "Concurrent job limit reached", "code": "rate_limited"},
        status=429, headers={"Retry-After": "60"},
    )
```

The gate lives in `manifests/views.py` so record creation and the count run in the same transaction (AD-7). The count is non-atomic; occasional over-admission by one is acceptable.

### Dispatch (AD-10) & status ownership (AD-12)

- Always `pipeline_task.delay_on_commit(...)` from the view — never `.delay()`/`.apply_async()` without `using=connection`. Worker must not read stale DB state before commit.
- `SBOMJob.status` is set to `PENDING` exactly once (in the generate view). Every later write (`PROGRESS`/`SUCCESS`/`FAILED`) happens ONLY in Celery task code via `sbom/services.py`. DRF views read status, never write it (except that initial PENDING).

### Response shapes (solution-design.md §5.3)

202: `{task_id, status:"PENDING", status_url, estimated_seconds}`. Status poll: `{task_id, status, progress, current_step, created_at, completed_at}`. Error envelope: `{error, code}`.

### Project Structure Notes

- New app module `<project_slug>/sbom/` (models, services, selectors); the generate view is in `manifests/views.py` (AD-7), the status view in `sbom/views.py`.
- Depends on Story 3.1 (upload service, `ManifestUpload`) and Story 1.3 (`OrgScopedModel`, settings). The pipeline task dispatched here is defined in Story 3.5 — provide the task reference/signature so this story integrates; if 3.5 is not yet built, dispatch to a task stub whose real body 3.5 fills in.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2: Job Submission, Concurrency Gate & Status API]
- [Source: solution-design.md#3.3 sbom/ — SBOMJob model, status ownership]
- [Source: solution-design.md#5.3 Standard response shapes]
- [Source: solution-design.md#5.4 Concurrency gate]
- [Source: ARCHITECTURE-SPINE.md#AD-7 — Per-org concurrency gate]
- [Source: ARCHITECTURE-SPINE.md#AD-10 — delay_on_commit]
- [Source: ARCHITECTURE-SPINE.md#AD-12 — SBOMJob.status written only by Celery]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: prd.md#FR-3.5, FR-3.6, FR-3.7, FR-4.7, NFR-4.1]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
