---
baseline_commit: 8c87a23
---

# Story 22.19: Name the Running Phase on the Progress Bar

Status: review

> **Product-owner direction:** *"I want the progress bar on the job status page to update the text with the
> name of the phase that is currently being processed."*

## Story

As someone watching a job run,
I want the progress text to name the phase being worked on right now,
so that a long-running job looks like it is working rather than stuck.

**Context:** The text was already there. Story 6.2 put the phase name above the bar on the Job Status row,
and Story 21.11 added the same to the results page. **The analysis phases never wrote it.** Phases 4, 5 and
7 reported to Celery's result backend with `task.update_state` and stopped, while only the pipeline phases
mirrored to the job row — so a job sat at *"generate SBOM document — 45%"* for the whole analysis fan-out,
which on a real manifest is the longest part of the run. The bar looked stuck exactly when the most work
was happening.

## Acceptance Criteria

1. **Each analysis phase names itself on the job row** when it starts, not only when it ends.
2. **Progress never moves backwards.** The three analysis phases run concurrently in a chord whose order is
   undefined, and their bands are 55, 80 and 93.
3. **Phase 8 does not regress the bar.** It reports 95, below version currency's 97 end.
4. **A failed phase does not claim to have completed.** FR-4.5 keeps the job running, so the bar advances —
   but the label must stay honest.
5. **A finished job is never dragged back into progress** by a straggling group member.
6. **It reads properly on both surfaces**, without mangling "SBOM".
7. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — `advance_job_progress`: monotonic, race-safe, terminal-safe (AC: #2, #3, #5)**
- [x] **Task 2 — Mirror the analysis phases to the job row (AC: #1)**
- [x] **Task 3 — Move `_report` and phase 8 onto the same helper (AC: #3)**
- [x] **Task 4 — Label a failed phase "unavailable", not "complete" (AC: #4)**
- [x] **Task 5 — `capfirst` on both surfaces (AC: #6)**
- [x] **Task 6 — Gate (AC: #7)**

## Dev Notes

### Why a new service function rather than `update_job_status`

Progress reporting has a constraint status writing does not: it must never go backwards. The guard lives in
the UPDATE's own `WHERE` clause (`progress__lte`, plus a `status__in` whitelist) rather than in a
read-then-write, because two workers reporting at the same instant must not be able to interleave into a
regression. `__lte` and not `__lt` is deliberate — phase 8 persists at 97 and version currency *ends* at 97,
so rejecting equal values would freeze the label on the analysis phase through the final write.

### What the concurrency means for the label

With three phases in flight there is no single "current" phase. The furthest-along one wins, which is
truthful (it *is* being processed) and keeps the bar monotonic. On Windows the worker is `--pool=solo`, so
they run serially and the label simply follows.

### Traps

- **The completion write sits outside the try/except on purpose** — FR-4.5 keeps the job running when a
  phase fails, so the bar has to keep moving. That is exactly why it would otherwise stamp "complete" on a
  phase that produced nothing.
- **`capfirst`, never `title`.** Title-casing turns "generate SBOM document" into "Generate Sbom Document".
- **A test that runs a phase to completion cannot tell "named itself when it started" from "named itself
  when it finished."** See below.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- 15 new tests in `tests/unit/test_job_progress_phase_text.py`.
- **First ablation: the tests did NOT bite.** With the entry write removed, all 9 still passed — the
  phase ran to completion synchronously, so the completion write set the same label a moment later.
  Rewritten to assert the **sequence** of writes; the second ablation fails 3 of them, as it should.
- `pixi run ci` — **exit 0**, 942 tests, 97.24%.

### Completion Notes List

**The first version of these tests was worthless and the ablation is what said so.** Asserting the row's
final state cannot distinguish a phase that named itself on entry from one that named itself on exit,
because both leave the same row. Spying on the calls to `advance_job_progress` and asserting the *first* one
is the entry is what actually pins the behaviour the story is about.

**A failed phase used to say "complete".** Not part of the request, but visible the moment the analysis
phases started writing labels at all: the completion write is outside the try/except, so it ran regardless
of outcome. It now says "unavailable", which is the word the report tabs already use for the same state.

**Two latent regressions were fixed by moving everything onto one helper.** Phase 8 reports 95, below
version currency's 97 — harmless while the analysis phases wrote nothing, and a visible backwards jump the
moment they did.

### File List

**New (1)**
- `tests/unit/test_job_progress_phase_text.py` (15 tests)

**Modified (4)**
- `src/django_apps/inventory/sbom/services.py` — `advance_job_progress`
- `src/django_apps/inventory/tasks/analysis.py` — mirror to the row; honest completion label
- `src/django_apps/inventory/tasks/sbom_pipeline.py` — `_report` and phase 8 use the helper
- `src/django_apps/inventory/sbom/tables.py`, `templates/inventory/sbom/_job_progress.html` — `capfirst`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | The progress text now names the phase being worked on. The label had existed since Story 6.2, but the three analysis phases only reported to Celery's result backend and never to the job row — so a job read "generate SBOM document — 45%" for the whole analysis fan-out, the longest part of a real run. Added `advance_job_progress`, which is monotonic and race-safe in the UPDATE's own WHERE clause, because the phases run concurrently with bands of 55/80/93 and phase 8 reports 95. Also stopped a failed phase reporting "complete" — it now reads "unavailable", matching the report tabs. |
