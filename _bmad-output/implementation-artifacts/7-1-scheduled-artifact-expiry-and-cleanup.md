# Story 7.1: Scheduled Artifact Expiry & Cleanup

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want expired artifacts purged automatically every day,
so that storage does not grow unbounded while job history is preserved.

## Acceptance Criteria

1. Given a job that completed more than 10 days ago, when the daily cleanup runs, then its artifact blobs (SBOM + all analysis reports) are deleted from the storage backend and `result_key` on the `SBOMJob` and `artifact_key` on every related `AnalysisReport` are nulled (FR-8.1, FR-8.2, AD-6).
2. Given the cleanup selector, when it identifies expired jobs, then it uses `SBOMJob.objects.filter(artifacts_expire_at__lte=now(), result_key__isnull=False)` (AD-6 conventions).
3. Given any cleanup run, when artifacts are deleted, then the `SBOMJob` record and its metadata (status, package count, summary statistics) are retained indefinitely — never deleted (FR-8.1).
4. Given the cleanup task, when it is scheduled, then a Celery Beat entry runs it daily and the task routes to the `pipeline` queue (FR-8.2, AD-4).
5. Given the cleanup service function, when it is invoked, then it is a pure service-layer function reused by both the scheduled task and on-demand deletion (Story 7.2), taking plain inputs (AD-3).
6. Given a job whose artifacts were already cleaned, when the cleanup runs again, then it is skipped (its `result_key` is already null) — the operation is idempotent.
7. Given integration tests for the cleanup task, when `pixi run cov` runs, then expiry selection, storage deletion, and key-nulling are covered ≥90%.

## Tasks / Subtasks

- [ ] Task 1 — Shared cleanup service function (AC: #1, #3, #5, #6)
  - [ ] Add `delete_job_artifacts(job: SBOMJob) -> None` in `sbom/services.py` — the single deletion primitive reused by the scheduled task (this story) and on-demand deletion (Story 7.2)
  - [ ] Delete all S3/MinIO objects under the prefix `sbom-results/{org_id}/{task_id}/` via `django-storages` / boto3
  - [ ] Null `result_key` on the `SBOMJob`; null `artifact_key` on every related `AnalysisReport` (`job.reports.all()`) in one transaction
  - [ ] Never delete the `SBOMJob` or `AnalysisReport` rows — only blobs + keys (AC #3)
  - [ ] Guard for idempotency: if `result_key` is already null, return without touching storage (AC #6)
  - [ ] Accept plain `SBOMJob` input, return `None` — no `HttpRequest`/`Response`/`Task` coupling (AD-3)
- [ ] Task 2 — Expiry selector (AC: #2)
  - [ ] Add `get_expired_jobs() -> QuerySet[SBOMJob]` in `sbom/selectors.py` returning `SBOMJob.objects.filter(artifacts_expire_at__lte=now(), result_key__isnull=False)`
  - [ ] Confirm `artifacts_expire_at` is populated at job finalization as `completed_at + 10 days` (set in Story 3.4 `finalize_job`) — this selector depends on it
- [ ] Task 3 — Celery Beat cleanup task (AC: #1, #4, #6)
  - [ ] Add `expire_artifacts_task` in `tasks/sbom_pipeline.py` as `@shared_task`, routed to the `pipeline` queue
  - [ ] Iterate `get_expired_jobs()` and call `delete_job_artifacts(job)` per job; log a structured entry per job (`org_id`, `task_id`, count of blobs removed)
  - [ ] Register the Beat schedule in `backend/config/celery_app.py`: `expire-artifacts` → `crontab(hour=3, minute=0)` (nightly 03:00), `options={'queue': 'pipeline'}`
- [ ] Task 4 — Tests (AC: #7)
  - [ ] Integration test: seed a job with `artifacts_expire_at` in the past + a `result_key` + related `AnalysisReport`s with `artifact_key`s and objects in the test MinIO bucket; run the task; assert blobs gone, keys nulled, job + report rows still present
  - [ ] Test the selector excludes not-yet-expired jobs and already-cleaned jobs (`result_key` null)
  - [ ] Test idempotency: run the task twice; second run performs no storage calls and raises nothing
  - [ ] Test cross-org safety: cleanup operates system-wide (Beat is not org-scoped) but only ever deletes each job's own `sbom-results/{org_id}/{task_id}/` prefix

## Dev Notes

### Cleanup mechanics (solution-design.md § 4.5 — authoritative)

```python
# backend/config/celery_app.py
app.conf.beat_schedule = {
    'expire-artifacts': {
        'task': 'tasks.sbom_pipeline.expire_artifacts_task',
        'schedule': crontab(hour=3, minute=0),   # nightly at 03:00
        'options': {'queue': 'pipeline'},
    },
}
```

Cleanup selector (AD-6 / consistency convention):

```python
SBOMJob.objects.filter(
    artifacts_expire_at__lte=now(),
    result_key__isnull=False,
)
```

For each matched job: delete all S3 objects under `sbom-results/{org_id}/{task_id}/`; null `result_key` on the job; null `artifact_key` on all related `AnalysisReport` rows. **The job record is never deleted** — status, package count, and summary statistics are retained indefinitely (FR-8.1).

### Why the deletion logic is a shared service (AD-3)

Story 7.2 (manual + bulk delete) must reuse the exact same `delete_job_artifacts(job)` function — no duplicated deletion logic across the scheduled task and the API endpoint. This story owns that primitive; Story 7.2 only wires views to it. Keep it a pure service function (plain input, no HTTP/Celery types) so both callers work unmodified.

### Queue routing (AD-4)

The cleanup task routes to the `pipeline` queue, not `analysis` — it is low-frequency housekeeping that must not compete with vulnerability-scan workloads on the `analysis` queue. A future third `cleanup` queue is deferred (spine Deferred); do not add it now.

### Storage paths (solution-design.md § 6.1)

All artifacts for a job live under `sbom-results/{org_id}/{task_id}/`: `sbom.{ext}`, `vuln.json`, `licenses.json`, `graph.svg`, `versions.json`. Deleting the whole prefix removes every blob for the job in one sweep.

### Expiry timestamp origin (solution-design.md § 3.3)

`SBOMJob.artifacts_expire_at` is set to `completed_at + 10 days` at job finalization (Story 3.4). This story only reads it; it does not set it.

### Idempotency

Because the selector filters `result_key__isnull=False`, an already-cleaned job is never re-selected. The service function additionally short-circuits if `result_key` is null, so direct re-invocation (from Story 7.2 retries) is also safe.

### Testing standards

- Integration tests hit real DB + test MinIO bucket (`@pytest.mark.integration`), broker `memory://`, and must leave the bucket/DB as found (teardown fixture).
- structlog only — never `print()`; bind `org_id`/`task_id` on cleanup log lines.
- ≥90% coverage on the cleanup service, selector, and task.

### Dependency / sequencing notes

- Depends on `SBOMJob` + `AnalysisReport` models and `finalize_job` setting `artifacts_expire_at` (Stories 3.4, 4.1). If Epic 3/4 are not yet built, this story cannot be exercised end-to-end — schedule after them.
- The Celery app + Beat plumbing exist from Epic 1 (Story 1.3); this story fills the previously-placeholder Beat schedule with the real `expire-artifacts` entry.
- Story 7.2 depends on this story's `delete_job_artifacts` service function.

### Project Structure Notes

- Deletion logic in `sbom/services.py` (mutation), selector in `sbom/selectors.py` (read), task in `tasks/sbom_pipeline.py`, schedule in `config/celery_app.py` — consistent with file-role conventions.
- No new models or migrations in this story.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.1: Scheduled Artifact Expiry & Cleanup]
- [Source: solution-design.md#4.5 Celery Beat — artifact cleanup]
- [Source: solution-design.md#6.1 Storage paths]
- [Source: solution-design.md#3.3 sbom/ — SBOMJob model]
- [Source: ARCHITECTURE-SPINE.md#AD-4 — Two Celery queues (Beat cleanup on pipeline)]
- [Source: ARCHITECTURE-SPINE.md#AD-6 — Storage triad]
- [Source: ARCHITECTURE-SPINE.md#AD-3 — Service layer purity]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Artifact cleanup]
- [Source: prd.md#FR-8.1, FR-8.2]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
