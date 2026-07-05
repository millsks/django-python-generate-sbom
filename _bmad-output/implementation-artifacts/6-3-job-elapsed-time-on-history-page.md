# Story 6.3: Job Elapsed Time on the History Page

Status: review

## Story

As a user, I want to see how long each job took to complete, so that I can gauge
processing time and spot slow runs at a glance.

## Acceptance Criteria

See Epic 6, Story 6.3 in `_bmad-output/planning-artifacts/epics.md`.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Backend: `JobListSerializer` gains a computed `elapsed_seconds`
  (`SerializerMethodField`) = `(completed_at - created_at).total_seconds()`, or
  `null` when `completed_at` is unset (still running / unfinished).
- Frontend: added `elapsed_seconds` to the `JobListItem` type, a shared
  `formatDuration` helper (`450ms` / `45s` / `1m 23s` / `2h 05m`, `—` when
  unknown), and an **Elapsed** column on the History table. Finished-at-list-time
  jobs use the serialized value; jobs that finish while polling use the live
  `completed_at`; still-running jobs show a live `created_at → now` duration
  refreshed by the existing 5s poll (Story 6.2). The table is server-paginated and
  not client-sortable, so the column is non-sortable (consistent with the others).
- Tests: backend serializer (completed → value, running → `null`) + endpoint field
  presence; frontend `formatDuration` unit tests + History column rendering.

### File List

- backend/generate_sbom/sbom/serializers.py
- backend/tests/unit/test_jobs_list.py
- frontend/src/api/jobs.ts
- frontend/src/duration.ts (new)
- frontend/src/duration.test.ts (new)
- frontend/src/pages/HistoryPage.tsx
- frontend/src/pages/HistoryPage.test.tsx
