---
baseline_commit: 6e9533c
---

# Story 21.11: Live Job Progress via htmx Polling

Status: review

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

- [x] **Task 1 — Status partial view (AC: #1)** — Renders one job's live state; reads via the existing
  selector; org-scoped.
- [x] **Task 2 — Row polling (AC: #2, #3)** — `hx-get` + `hx-trigger="every 5s"` on non-terminal rows only;
  emit a response that removes the trigger once terminal.
- [x] **Task 3 — Results-page gate (AC: #4)** — Poll the progress view; swap in the full results on terminal.
- [x] **Task 4 — Error handling (AC: #5)** — Stop polling on 403/404; render the denial state.
- [x] **Task 5 — Tests + gate (AC: #6)**.

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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **638 passed**, coverage **96.29%**; frontend **223 passed**.
- **17 new tests** in `tests/unit/test_job_polling.py`.
- Routes: `ui-job-row` → `/history/row/<task_id>`, `ui-job-results` → `/results/<task_id>`,
  `ui-job-progress` → `/results/<task_id>/progress`.
- Trigger scoping verified on a mixed page: the running row carries
  `hx-trigger="every 5s"`; the SUCCESS and FAILED rows carry **no trigger and no URL**. A page
  of three finished jobs contains the string `hx-trigger` **zero** times.
- Self-termination verified by transition: the same row returns *with* a trigger while
  PROGRESS and *without* one after being moved to SUCCESS.
- `HX-Refresh` absent while running, `"true"` once terminal.
- Cross-org and unknown task ids both **404** on all three endpoints.

### Completion Notes List

**The "single sanctioned way to poll" rule is enforced by a test, not just by intent.**
`useJobStatus.ts` existed so no component could add its own polling loop. The server-side
equivalent is `tables.poll_attrs`, the only producer of an `hx-trigger` anywhere in the app —
and `test_the_trigger_is_produced_in_exactly_one_place` greps the app tree and fails if a
second producer appears. That matters because Stories 21.13–21.16 add four more tab pages that
could each grow a poller.

**Polling self-terminates from the server, which is the robust direction.** The refreshed row is
produced by the same `poll_attrs`, so a job that finishes between polls comes back **without**
a trigger and htmx simply stops. Nothing has to notice terminality and cancel a timer. The same
idea drives the results page: the progress fragment's response carries `HX-Refresh: true` once
the job is terminal, so the page reloads into the completed view without the client deciding
anything.

**Terminal rows issue no requests at all** — the Dev Notes call this the single biggest load
difference from a naive implementation, and it is asserted directly rather than inferred.
`get_job` is a single indexed lookup with `select_related("manifest")` and touches no artifact
storage, so a page of 25 running jobs is 25 cheap queries per 5s rather than anything involving
blobs.

**The row partial reuses `JobTable` rather than duplicating cell markup.** The polling view
constructs a one-row `JobTable` and the template emits only the `<tr>` wrapper, so the badge,
progress bar, and elapsed renderers are shared with the full table — there is no second copy of
a cell to drift.

**Elapsed freezes as a property of the data, not by stopping a timer.** `render_elapsed`
measures to `completed_at or timezone.now()`, so a running job advances every poll and a
finished one is fixed. The test asserts two consecutive reads of a finished row are byte
identical, which would fail if the end point were still moving.

**Errors stop rather than spin.** A cross-org or unknown task id is a 404 on all three
endpoints — identical responses, no existence leak (AD-2) — and htmx does not re-issue a
polling request after a 404, so a denied row is left as it was instead of retrying forever.

**Scope split with Story 21.12, stated plainly.** This story claims `/results/<task_id>` and
owns the **gate**: progress while running, transition on terminal. What renders *behind* the
gate is a deliberate placeholder — 21.12 replaces it with the tabbed results shell and the
Overview tab. Splitting it this way is what the story order implies (21.12 is listed as
downstream of this one), and it means the history page's "View" link and the upload redirect
now both reverse `ui-job-results` instead of pointing at the SPA.

**Not done here.** No websockets or SSE — polling at the SPA's interval was the brief, and
changing the transport would have changed the load profile without being asked. The results
page shows no report data yet.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (4)**
- `src/django_apps/inventory/templates/inventory/sbom/_job_row.html` — the polled row wrapper
- `src/django_apps/inventory/templates/inventory/sbom/_job_progress.html` — the polled fragment
- `src/django_apps/inventory/templates/inventory/sbom/results.html` — the gate (21.12 fills it in)
- `tests/unit/test_job_polling.py` (17 tests)

**Modified (5)**
- `src/django_apps/inventory/sbom/services.py` — `TERMINAL_STATUSES`
- `src/django_apps/inventory/sbom/tables.py` — `poll_attrs`, `POLL_INTERVAL`, row triggers,
  phase/progress and failure-reason rendering, live elapsed
- `src/django_apps/inventory/sbom/pages.py` — `JobRowPartialView`, `JobResultsView`,
  `JobProgressPartialView`; the upload redirect now reverses `ui-job-results`
- `src/django_apps/inventory/urls_pages.py`, `src/config/urls.py` — three routes; `results` freed
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Added htmx polling at the SPA's 5-second interval. Only non-terminal rows carry a trigger, and because the refreshed markup is produced by the same helper, a job that finishes mid-poll returns untriggered and polling self-terminates. The results page gates on completion, transitioning via an `HX-Refresh` header the server sets. Elapsed time advances while running and freezes on completion as a property of the data. Cross-org and unknown ids 404 identically, so polling stops rather than spinning. A test asserts the trigger is produced in exactly one place, carrying over the SPA's "no per-component polling loops" rule. `pixi run ci` exit 0; 638 backend tests at 96.29%. |
