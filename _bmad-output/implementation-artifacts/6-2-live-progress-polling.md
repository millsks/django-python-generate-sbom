# Story 6.2: Live Progress Polling

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want in-progress jobs to update their progress automatically,
so that I can watch a job advance without manually refreshing.

## Acceptance Criteria

1. Given a job in `PENDING` or `PROGRESS` state on the dashboard, when the dashboard is open, then its progress percentage and current phase name are polled from `GET /api/v1/sbom/status/{task_id}/` every 5 seconds and updated in place.
2. Given the polling implementation, when a component needs job status, then it uses the shared `useJobStatus(taskId)` hook — no bespoke polling logic per component.
3. Given a job that transitions to `SUCCESS` or `FAILURE` while being polled, when the terminal state is received, then polling for that job stops and the row updates to its final state (with results link on success, failure reason on failure).
4. Given no WebSocket infrastructure exists, when live updates occur, then they are achieved purely through the 5-second HTTP polling.
5. Given the dashboard has no in-progress jobs, when it is open, then no status polling requests are issued.

## Tasks / Subtasks

- [ ] Task 1 — Shared `useJobStatus(taskId)` hook (AC: #1, #2, #3, #4)
  - [ ] Create `frontend/src/api/useJobStatus.ts` (or `frontend/src/hooks/useJobStatus.ts` sourcing its fetch from `src/api/jobs.ts`) — the single shared polling primitive (AD-5)
  - [ ] Poll `GET /api/v1/sbom/status/{taskId}/` on a 5-second interval; expose `{ status, progress, current_step }`
  - [ ] Read from the fetch function in `frontend/src/api/jobs.ts` — no direct `fetch` in the hook/component (AD-5)
  - [ ] Stop the interval when `status` is `SUCCESS` or `FAILED` (terminal) and clean up the timer on unmount
- [ ] Task 2 — Wire polling into HistoryPage rows (AC: #1, #3, #5)
  - [ ] For rows whose status is `PENDING`/`PROGRESS`, subscribe to `useJobStatus(taskId)` and update progress % + current phase in place
  - [ ] On terminal transition, stop polling that row and re-render its final state: results link on `SUCCESS`, failure reason on `FAILED` (reuses Story 6.1's badge + failure summary)
  - [ ] Ensure rows already in a terminal state on first load never start polling (AC #5)
- [ ] Task 3 — No-op when idle (AC: #5)
  - [ ] Confirm that when the current page has zero in-progress jobs, no status requests are issued (guard the hook subscription on non-terminal status)
- [ ] Task 4 — Tests
  - [ ] Frontend: hook polls at 5s, stops on terminal state, cleans up timers on unmount; no requests when initial status is terminal
  - [ ] Frontend: HistoryPage updates an in-progress row's progress/phase in place and swaps to final state on transition
  - [ ] Backend `pixi run ci` remains green (this story is frontend-only; no backend changes expected)

## Dev Notes

### Polling model (FR-7.2; solution-design.md §7.2, §4.3)

The React SPA polls `GET /api/v1/sbom/status/{taskId}/` every 5 seconds via the shared `useJobStatus(taskId)` hook until `status` is `SUCCESS` or `FAILED`. The status endpoint reads `SBOMJob.progress` and `SBOMJob.current_step` from PostgreSQL (Celery task code writes progress there via the `update_job_status` service function). No WebSocket / Django Channels — polling is the v1 baseline (Channels is a deferred drop-in upgrade). [Source: solution-design.md#7.2, #4.3; ARCHITECTURE-SPINE.md#Deferred]

### Status poll response shape (solution-design.md §5.3)

```json
{
  "task_id": "3fa85f64...",
  "status": "PROGRESS",
  "progress": 62,
  "current_step": "vulnerability scan",
  "created_at": "2026-07-03T14:00:00Z",
  "completed_at": null
}
```

`status` ∈ `PENDING | PROGRESS | SUCCESS | FAILED`. Terminal states are `SUCCESS` and `FAILED`. [Source: solution-design.md#5.3]

### Shared-hook convention (AD-5)

`useJobStatus(taskId)` is the single sanctioned polling primitive — no per-component polling loops, no direct `fetch` in components. The fetch itself lives in `frontend/src/api/`. [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Frontend data]

### Dependency / sequencing notes

- Depends only on Story 6.1 (the HistoryPage table + `frontend/src/api/jobs.ts`) and the status endpoint `GET /api/v1/sbom/status/{task_id}/` already built in Epic 3 Story 3.2.
- Frontend-only; no backend changes expected. The status endpoint contract is fixed upstream.
- The same `useJobStatus` hook is reused by `ResultsPage` in Epic 5 — build it as a general primitive here, not a HistoryPage-specific one.

### Project Structure Notes

- Frontend: `frontend/src/api/useJobStatus.ts` (or `frontend/src/hooks/useJobStatus.ts` importing from `src/api/jobs.ts`), plus edits to `frontend/src/pages/HistoryPage.tsx`.
- No new backend files; no new endpoints.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.2: Live Progress Polling]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA: REST API only]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Frontend data]
- [Source: ARCHITECTURE-SPINE.md#Deferred — WebSocket / Django Channels]
- [Source: solution-design.md#7.2 Page structure]
- [Source: solution-design.md#4.3 Progress signalling]
- [Source: solution-design.md#5.3 Standard response shapes]
- [Source: prd.md#FR-7.2]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
