# Story 3.5: Pipeline Orchestration, Progress & Timeout Handling

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the SBOM pipeline,
I want an orchestrated eight-phase Celery chain with progress reporting and timeout handling,
so that jobs run end-to-end reliably and failures are surfaced cleanly to the user.

## Acceptance Criteria

1. Given a dispatched job, when the pipeline runs, then it executes as a Celery chain: Phase 1 → 2 → 3 → (parallel group of Phases 4–7, stubbed as a no-op group in this epic) → chord callback → Phase 8, with Phases 1–3 and 8 on the `pipeline` queue (FR-4.1, FR-4.2, AD-4).
2. Given the analysis group is stubbed in this epic, when the chord callback runs, then it aggregates an empty analysis result and proceeds to Phase 8 — Epic 4 replaces the stub with the four real analysis tasks without changing the orchestration shape.
3. Given each phase boundary, when a phase begins, then progress is reported via `task.update_state()` matching the thresholds in FR-4.2 (0–15, 15–40, 40–55, 55–80, 80–88, 88–93, 93–97, 97–100), so a polling client sees monotonically increasing progress (FR-4.1).
4. Given a job exceeds the 25-minute soft limit, when `SoftTimeLimitExceeded` is raised, then the task catches it, marks the job `FAILED` with reason `"soft_timeout"`, releases held resources, and returns no partial SBOM (FR-4.6).
5. Given a job exceeds the 30-minute hard limit and the worker is force-terminated, when the next status poll or cleanup sweep runs, then the job is marked `FAILED` with reason `"hard_timeout"` (FR-4.6).
6. Given either timeout reason is set, when the user views job status, then the failure reason (`soft_timeout` / `hard_timeout`) is surfaced in the status response (FR-4.6).
7. Given a Celery task failure at any phase, when the failure is logged, then the log entry includes the full traceback and the manifest format that triggered it (NFR-6.2).
8. Given all task definitions, when they are declared, then each uses `@shared_task` with no direct Celery app import in the task module (AD-10).
9. Given a manifest of <50 packages on a single 4-core worker, when the full pipeline runs, then it completes within the NFR-2.1 target (under 35 seconds).

## Tasks / Subtasks

- [ ] Task 1 — Assemble the chain (AC: #1, #2, #8)
  - [ ] `tasks/sbom_pipeline.py`: build the canvas per Dev Notes — `chain(detect_and_parse → resolve → generate → group(4 analysis stubs) | aggregate_analysis_results → persist)`
  - [ ] Analysis group is FOUR no-op stub tasks returning the standard envelope with empty summaries; `aggregate_analysis_results` collects them and proceeds
  - [ ] All `@shared_task`; no Celery app import in the module (AD-10)
  - [ ] Route Phases 1–3, 8 + chord callback to `pipeline`; the (stub) analysis group to `analysis` (AD-4)
- [ ] Task 2 — Progress signalling (AC: #3)
  - [ ] Each phase calls `task.update_state(state='PROGRESS', meta={'progress': N, 'current_step': '<phase>'})` at start, matching FR-4.2 thresholds
  - [ ] Persist progress to `SBOMJob.progress`/`current_step` via `update_job_status` so the status endpoint (Story 3.2) reflects it; ensure monotonic increase
- [ ] Task 3 — Soft-timeout handling (AC: #4, #6)
  - [ ] Configure `CELERY_TASK_SOFT_TIME_LIMIT=1800`, `CELERY_TASK_TIME_LIMIT=2100` (settings from Story 1.3)
  - [ ] Catch `SoftTimeLimitExceeded` in the chain header/phase tasks → `update_job_status(status='FAILED', failure_reason='soft_timeout')`, release resources, no partial SBOM
- [ ] Task 4 — Hard-timeout sweep (AC: #5, #6)
  - [ ] On status poll (Story 3.2) or a cleanup sweep, detect jobs whose worker was force-killed (still PENDING/PROGRESS past the hard limit) → mark `FAILED` reason `hard_timeout`
  - [ ] Surface both timeout reasons in the status response
- [ ] Task 5 — Failure logging (AC: #7)
  - [ ] On any task failure, log full traceback + manifest format via structlog (NFR-6.2), bound `org_id`+`task_id`
- [ ] Task 6 — Tests (AC: all)
  - [ ] Integration: full chain against a small fixture completes, status transitions PENDING→PROGRESS→SUCCESS, progress monotonic, analysis stubs return empty (broker='memory://')
  - [ ] Unit: SoftTimeLimitExceeded → FAILED soft_timeout, no artifact
  - [ ] Unit: hard-timeout sweep marks stale job FAILED hard_timeout
  - [ ] Assert the stub group is swappable (shape stable for Epic 4)
  - [ ] Perf smoke: <50-package fixture within NFR-2.1 target
  - [ ] ≥90% coverage; `pixi run ci` exits 0

## Dev Notes

### Canvas pattern (solution-design.md §4.1) — analysis group STUBBED this epic

```python
# tasks/sbom_pipeline.py
from celery import chain, group, shared_task

pipeline = chain(
    detect_and_parse_manifest.si(manifest_key, org_id, task_id),   # Phase 1 (Story 3.3)
    resolve_transitive_deps.s(),                                   # Phase 2 (Story 3.3)
    generate_sbom_document.s(output_format),                       # Phase 3 (Story 3.4)
    group(                                                         # Phases 4–7 — NO-OP STUBS here
        scan_vulnerabilities.s(),      # stub → envelope, empty summary
        analyze_licenses.s(),          # stub
        build_dependency_graph.s(),    # stub
        check_version_currency.s(),    # stub
    ) | aggregate_analysis_results.s(),                            # chord callback (pipeline queue)
    persist_artifacts.s(),                                         # Phase 8 (Story 3.4)
)
```

Epic 4 Story 4.6 replaces the four stubs with the real analysis tasks WITHOUT changing the chain shape. Keep the chord-callback contract identical: each analysis task returns `{"report_type","artifact_key","summary","failed","failure_reason"}` (spine convention); the stubs return this with empty/false values.

### Phase / queue / progress map (solution-design.md §4.2; FR-4.2; AD-4)

| Phase | Queue | Progress |
|---|---|---|
| 1 detect & parse | pipeline | 0→15 |
| 2 resolve | pipeline | 15→40 |
| 3 generate | pipeline | 40→55 |
| 4 vuln (stub) | analysis | 55→80 |
| 5 license (stub) | analysis | 80→88 |
| 6 graph (stub) | analysis | 88→93 |
| 7 version (stub) | analysis | 93→97 |
| 8 persist | pipeline | 97→100 |

Progress via `task.update_state(state='PROGRESS', meta={'progress': N, 'current_step': '<phase name>'})`, mirrored to `SBOMJob` so the status endpoint reports it. Client polls every 5s (Epic 6).

### Timeout handling (FR-4.6; solution-design.md §4.4)

- Soft (25 min / `CELERY_TASK_SOFT_TIME_LIMIT=1800`): catch `SoftTimeLimitExceeded` → `FAILED` reason `soft_timeout`, release resources, NO partial SBOM.
- Hard (30 min / `CELERY_TASK_TIME_LIMIT=2100`): worker force-killed; a status-poll/cleanup sweep marks the job `FAILED` reason `hard_timeout`.
- Both reasons surfaced in the status response and job history.

### Guardrails

- `@shared_task` everywhere; no Celery app import in task modules (AD-10).
- `delay_on_commit()` dispatch is owned by the generate view (Story 3.2); this story owns the chain body.
- Status writes only via `sbom/services.py` (AD-12).
- Analysis-task failures do NOT abort the chord (matters once Epic 4 lands); the stub already models this by always returning an envelope.

### Project Structure Notes

- `<project_slug>/tasks/sbom_pipeline.py` (chain + Phase 1–3/8 wiring + timeout handling); analysis stubs may live here or in `tasks/analysis.py` (Epic 4 replaces them in `tasks/analysis.py`).
- Depends on Stories 3.2 (SBOMJob, status seam, dispatch target), 3.3 (Phase 1–2 bodies), 3.4 (Phase 3/8 bodies). This story makes Epic 3 independently completable and end-to-end runnable with empty analysis.
- Does NOT depend on Epic 4; Epic 4 depends on the stub contract defined here.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.5: Pipeline Orchestration, Progress & Timeout Handling]
- [Source: solution-design.md#4.1 Canvas pattern]
- [Source: solution-design.md#4.2 Phase breakdown]
- [Source: solution-design.md#4.3 Progress signalling]
- [Source: solution-design.md#4.4 Error handling]
- [Source: ARCHITECTURE-SPINE.md#AD-4 — Two Celery queues]
- [Source: ARCHITECTURE-SPINE.md#AD-10 — delay_on_commit / @shared_task]
- [Source: ARCHITECTURE-SPINE.md#AD-12 — status written only by Celery]
- [Source: prd.md#FR-4.1, FR-4.2, FR-4.6, NFR-2.1, NFR-6.2]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

- Eager chords (`task_always_eager`) still reach the configured result backend (Redis) to synchronize the chord counter — an in-process end-to-end chord run isn't available without live infra. The canvas is validated **structurally** (shape test on `build_pipeline`) and **behaviorally** (a full phase-by-phase sequence run in the integration test); Celery owns chord-execution correctness.

### Completion Notes List

- **Canvas** (`build_pipeline`): `chain(detect.si(task_id) → resolve.s → generate.s → chord(group(4 analysis stubs), aggregate.s(task_id)) → persist.si(task_id))`. Celery folds `persist` into the chord body (`aggregate | persist`) — verified in the shape test. `task_id` threads the whole chain; only keys/counts flow through the result backend, never blobs (AD-6, see [[phase3-writes-blob-not-phase8]]).
- **Analysis group stubbed** (AC #2): four no-op tasks on the `analysis` queue, each returning the standard envelope `{report_type, artifact_key, summary, failed, failure_reason}` with empty/false values. `aggregate_analysis_results` collects them and proceeds. Epic 4 replaces the four bodies without changing the shape.
- **Progress** (AC #3): sequential phases mirror progress to `SBOMJob` (monotonic 5→20→45→95→97→100); the parallel stubs report Celery state only (55/80/88/93) so concurrent updates can't make the polled DB progress regress.
- **Soft timeout** (AC #4/#6): `_phase_guard` context manager catches `SoftTimeLimitExceeded` → `FAILED` reason `soft_timeout`, no partial SBOM. `celery.exceptions` import is not a Celery app import (AD-10 ok).
- **Hard timeout** (AC #5/#6): a force-killed worker can't mark itself, so `mark_stale_job_timed_out` (run on status poll) fails a still-PENDING/PROGRESS job older than `CELERY_TASK_TIME_LIMIT` with reason `hard_timeout`. Both reasons are surfaced via a new `failure_reason` field in the status response.
- **Failure logging** (AC #7): `_phase_guard` logs the full traceback + manifest format on any phase failure.
- **Refinement of Story 3.4 tasks:** Phase 3 now records the artifact key + package count on the job (`services.record_generation`), and Phase 8 (`persist_artifacts`) finalizes by `task_id` alone (reads the DB) rather than receiving a `prev` dict — so the group in the middle of the chain doesn't have to forward generation context. Updated the two affected Story 3.4 tests.
- Gate: `pixi run ci` exits 0 — 128 tests, 95.54% coverage (`sbom_pipeline.py` 99%).

### File List

- backend/generate_sbom/tasks/sbom_pipeline.py (chain assembly, phases, stubs, timeout guard)
- backend/generate_sbom/sbom/services.py (record_generation, mark_stale_job_timed_out)
- backend/generate_sbom/sbom/views.py (hard-timeout sweep + failure_reason in status)
- backend/tests/unit/test_pipeline_orchestration.py (new)
- backend/tests/integration/test_pipeline_orchestration.py (new)
- backend/tests/unit/test_sbom_generation.py (persist now keyed by task_id)
- backend/tests/integration/test_sbom_storage.py (persist now keyed by task_id)
