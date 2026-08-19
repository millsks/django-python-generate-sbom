---
baseline_commit: e231a35
---

# Story 22.20: Report Progress as a Task List

Status: review

> **Product-owner design.** After two failed attempts to make a single status line work, the product owner
> proposed the shape that actually fits: *"Do we list all the tasks in a table with the dots cycling next to
> it while we have the progress bar at the bottom that increases with each finished task and when each task
> does finish it gets a [COMPLETE] or [ERROR] next to it."* It resolves the problem the earlier attempts kept
> hitting, rather than working around it.

## Story

As someone watching a job run,
I want to see every task in the pipeline with its own state,
so that I can tell what is running, what has finished, and what went wrong.

**Context:** Story 22.19 tried twice to make `SBOMJob.current_step` — one string — describe the pipeline, and
could not. The three analysis tasks run **concurrently** in a chord (AD-4), so at times two really are
running and a sentence can only name one. The percentages were hand-picked per phase (5, 20, 45, 55, 80, 93,
95, 97) and had drifted until two different tasks both reported 93%. **The display and the data model
disagreed because the model could not express what was happening.**

## Acceptance Criteria

1. **A row per task per job**, seeded at submission so the whole pipeline is visible before it starts.
2. **Each task writes only its own row** — the three concurrent analysis tasks cannot race each other.
3. **The bar is derived**, not reported: equal share per task, advancing only as tasks finish.
4. **`Task: ` prefix**, `[COMPLETE]` / `[ERROR]` on finish, and no "complete" label on a running task.
5. **Animated dots** beside a running task, cycling 1→10→1, one per second, restarting per task — and never
   blanking, including across the five-second htmx swap.
6. **A failed task still advances the bar** (FR-4.5) and reads `[ERROR]`, not `[COMPLETE]`.
7. **The compact surfaces keep working** — the Job Status table cell and the API's `current_phase`.
8. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — `pipeline_tasks.py`: declare the sequence once, derive the share (AC: #3)**
- [x] **Task 2 — `JobTask` model + migration `0004` (AC: #1, #2)**
- [x] **Task 3 — `seed_job_tasks` / `start_job_task` / `finish_job_task` (AC: #1, #2, #6)**
- [x] **Task 4 — `_phase_guard` owns the lifecycle, so a phase cannot forget (AC: #2, #6)**
- [x] **Task 5 — The task list template and `task-dots.js` (AC: #4, #5)**
- [x] **Task 6 — Keep `current_step` in step for the compact cell and the frozen API (AC: #7)**
- [x] **Task 7 — Gate (AC: #8)**

## Dev Notes

### Why a table rather than a field

`JobTask` gives each task its own row, so the three concurrent analysis tasks never touch the same record —
no read-modify-write, no race. A JSON blob on `SBOMJob` would have needed one, and could not have been
updated safely from three workers at once.

It also makes the bar honest: counting terminal rows out of eight cannot produce two tasks at 93%.

### The dots went through five designs

1. **Derived from `started_at`** — elegant, and it read badly. A task already running when its row first
   appeared started mid-cycle, concurrent tasks each showed a different count, and client/server clock skew
   shifted everything. Reported as *"jumping straight to a larger number"*.
2. **A counter cycling 0→10** — literally what was asked for, and wrong in practice: the zero renders as
   nothing, so once per cycle the dots vanished. Reported as *"they disappear sometimes only to reappear
   with the next dot"*.
3. **A counter cycling 1→10** — always at least one period on screen. Fixed the blank, exposed the next one.
4. **Repaint on `htmx:afterSwap`** — the counter survived the five-second swap, but the *markup* did not: the
   replacement span arrives empty, so the dots vanished until the next tick. Reported as *"1 dot to 5 dots,
   then disappear, then come back for 6 through 10"* — the 5 being the poll interval, not the cycle.
   `render(false)` repaints without advancing.
5. **No dwell at ten.** A one-second hold on the tenth dot was tried to make the wrap deliberate and read as
   a stall. The cycle is a plain 1..10 and straight back to 1.

The counter lives in the script, not the markup, because htmx swaps the fragment every five seconds and any
state stored inside it would restart on each swap.

### Traps

- **Seeding is not guaranteed.** `start_job_task` upserts, so a job created off the `create_job` path still
  reports rather than rendering an empty list with nothing to explain it. Found by a trace script that
  created its job directly — the display was silently blank.
- **`current_step` is still load-bearing.** The Job Status *table* has one cell per job, and
  `/api/v1/sbom/status/{id}/` exposes `current_phase` under a frozen contract (Story 21.24 AC #9). Dropping
  it would have left every row reading "Queued".
- **Labels are escaped.** "Detect & parse manifest" renders `&amp;`; a raw comparison passes on seven labels
  and fails on the eighth.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- 21 tests in `tests/unit/test_job_task_list.py`; `test_job_progress_phase_text.py` (16) deleted with the
  mechanism it covered.
- **Traced against a real worker** (`scratchpad/trace_phases.py`, sampling every 50 ms). The run shows the
  bar stepping 12% per task and all three analysis tasks running together:

```
 38%  running=[]                        done=[detect, resolve, generate]
 38%  running=[vuln, license, version]  done=[detect, resolve, generate]
 50%  running=[vuln, version]           done=[…, license]
 62%  running=[version]                 done=[…, vuln]
100%  SUCCESS                           done=[all eight]
```

- `pixi run ci` — **exit 0**, 950 tests, 97.23%.

### Completion Notes List

**The product owner's design was better than the one being iterated on.** Two attempts at a single status
line failed for the same reason each time — the model could not represent concurrent tasks — and a list
makes that a non-problem rather than something to work around.

**The bar is derived, which is the property that makes it trustworthy.** No phase picks its own number, so
adding a task cannot overweight the others and two tasks cannot claim the same point.

**`_phase_guard` owns start and finish.** Placing them at each call site is how the old hand-placed progress
calls drifted; a phase that returns without reporting is now impossible.

**Two rendering bugs were found by the product owner, not by the tests**, both after a green gate: the dots
jumping, and the browser tab still reading "History" (Story 22.17's rename missed the `{% block title %}`,
and none of its guards looked at rendered titles). Both now have assertions that fail without the fix.

### File List

**New (4)**
- `src/django_apps/inventory/sbom/pipeline_tasks.py`
- `src/django_apps/inventory/migrations/0004_jobtask.py`
- `src/django_service/static/js/task-dots.js`
- `tests/unit/test_job_task_list.py` (21 tests)

**Deleted (1)**
- `tests/unit/test_job_progress_phase_text.py`

**Modified (10)**
- `sbom/{models,services,pages}.py`, `inventory/models.py`
- `tasks/{sbom_pipeline,analysis}.py`
- `templates/inventory/sbom/{_job_progress,job_status}.html`, `django_service/templates/base.html`
- `tests/unit/{test_app_labels,test_pipeline_phases,test_pipeline_orchestration,test_job_polling,test_landing_page,test_job_status_rename}.py`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Replaced the single-line progress display with a list of the pipeline's eight tasks, each with its own state. A `JobTask` row per task means the three concurrent analysis tasks never race, and lets the page show two of them running at once — which a single `current_step` string could never do, and which is why Story 22.19's two attempts both failed. The bar is now derived from finished tasks (equal share each) rather than hand-picked bands that had drifted until two tasks both reported 93%. Running tasks animate 1→10 dots; finished ones read `[COMPLETE]` or `[ERROR]`. Also fixed the browser tab still reading "History" — Story 22.17's rename missed the title block, and its guards did not look at rendered titles. |
