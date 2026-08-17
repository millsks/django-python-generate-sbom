# Story 21.11: Live Job Progress via htmx Polling

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.10**. Adds live updates to the history rows that story built, and
> establishes the polling gate that Story 21.12's results page depends on.

## Story

As a user,
I want in-progress jobs to update themselves on screen,
so that I can watch a job's phase and percentage without reloading the page.

## Acceptance Criteria

1. **htmx polling replaces the `useJobStatus` hook.**
   Given `useJobStatus` polls `GET /sbom/status/{taskId}/` every 5s (`POLL_MS = 5000`) and stops at a terminal
   status, when it is converted, then a partial-rendering view polled by htmx at the **same 5-second interval**
   replaces it, reading status through the existing selector rather than over HTTP (**AD-1**), and **polling
   stops** once the job reaches a terminal state — verified by asserting no further requests are issued.
2. **Only the affected row swaps.**
   Given in-progress history rows show the current phase, percentage, and a progress bar (Story 6.2), when a
   row polls, then only that row's partial is swapped, rows already in a terminal state **never poll at all**,
   and a row that completes or fails during polling swaps to its final state in place — including the failure
   reason for a failed job.
3. **Elapsed time ticks then freezes.**
   Given a still-running job's elapsed time is computed live from `created_at` and a finished job uses its
   recorded duration (Story 6.3), when the row refreshes, then elapsed time updates with each poll while
   running and freezes at the recorded duration once the job finishes.
4. **The results page gates on completion.**
   Given `ResultsPage.tsx` shows a progress view until the job reaches a terminal state, when a user opens
   results for a running job, then they see the current phase and progress bar, the page polls at the same
   interval, and it renders the full results view once the job terminates — without a manual refresh.
5. **Errors do not spin forever.**
   Given a cross-org or unknown job surfaces as 403/404 with no existence leak, when polling encounters one,
   then polling **stops** and the appropriate denial state renders rather than retrying indefinitely.
6. **Gate green.**
   When the story completes, then tests assert the terminal-state stop condition, the per-row swap, the
   elapsed-time freeze, the results-page transition, and the error stop, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — Status partial view (AC: #1)** — Renders one job's live state; reads via the existing
  selector; org-scoped.
- [ ] **Task 2 — Row polling (AC: #2, #3)** — `hx-get` + `hx-trigger="every 5s"` on non-terminal rows only;
  emit a response that removes the trigger once terminal.
- [ ] **Task 3 — Results-page gate (AC: #4)** — Poll the progress view; swap in the full results on terminal.
- [ ] **Task 4 — Error handling (AC: #5)** — Stop polling on 403/404; render the denial state.
- [ ] **Task 5 — Tests + gate (AC: #6)**.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/hooks/useJobStatus.ts` — `POLL_MS = 5000`; described as "The single sanctioned way to poll
  `GET /sbom/status/{taskId}/` — no per-component polling loops"; stops when
  `TERMINAL_STATUSES.includes(next.status)`; `JobStatusError = 'denied' | 'error'` where 403/404 both map to
  `'denied'` ("Cross-org and unknown jobs both surface as 403/404 — no existence leak, AD-2").
- `useJobStatus` has an `enabled` option so terminal rows issue no requests at all (`HistoryPage.tsx:71-73`).
- Live fields consumed: `status`, `current_phase`, `progress`, `failure_reason`, `completed_at`,
  `artifacts_available`, `artifacts_expire_at`.
- Elapsed logic (`HistoryPage.tsx:85-93`): serialized `elapsed_seconds` when present; else
  `completed_at - created_at`; else `now - created_at` while in progress.
- `ResultsPage.tsx:80-92` — renders the phase + `LinearProgress` until `TERMINAL_STATUSES.includes(status)`.

### The "single sanctioned way" rule carries over

The SPA deliberately centralised polling in one hook to prevent per-component loops. Keep the server-side
equivalent equally singular: **one** partial view and **one** trigger convention, reused by both the history
rows and the results gate. Do not let a later tab story add its own poller.

### htmx mechanics worth pinning down

- Use `hx-trigger="every 5s"` on the row/partial itself, and have the terminal response render **without** the
  trigger attribute so polling self-terminates — this is more robust than trying to cancel from the client.
- `hx-swap="outerHTML"` on the row partial keeps the swap scoped.

### Watch for

- **Polling load**: one request per in-progress row every 5s. With a page of 25 all-running jobs that is 5
  req/s from a single user. Confirm the status selector is cheap and does not re-query the artifact store.
- **Do not poll terminal rows** — this is the single biggest load difference between a correct and a naive
  implementation.

### Testing standards

- A test that renders a page with mixed terminal/non-terminal rows and asserts only the non-terminal ones
  carry a polling trigger.
- A test asserting the terminal response omits the trigger.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.11: Live Job Progress via htmx Polling]
- `frontend/src/hooks/useJobStatus.ts`, `frontend/src/pages/{HistoryPage,ResultsPage}.tsx`,
  `frontend/src/api/jobs.ts`, `generate_sbom/sbom/{views,selectors}.py`.
- Upstream: `21-10-job-history-table.md`. Downstream: `21-12-results-page-shell-and-overview-tab.md`.
- Architecture: AD-1 (no inter-app HTTP), AD-2 (no existence leak), AD-12 (status written only by task code).

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
