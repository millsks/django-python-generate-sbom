---
baseline_commit: cd68269
---

# Story 22.18: Drain the Test Worker's Pipe

Status: review

> **This is a bug fix, so the commit type is `fix:`** (global standards §5). Found by CI, and only
> identified on the **fourth** attempt.

## Story

As a maintainer,
I want the real-worker test to pass on Windows,
so that the one end-to-end proof of the containerless path is not permanently red on the platform the epic
exists to protect.

**Context:** Story 22.4's end-to-end test failed on Windows CI **three times**, always at
`progress=45`, always with `Task inventory.tasks.analysis.scan_vulnerabilities received` as the worker's
last line. Two earlier explanations were investigated and rejected; a third was implemented, was a genuine
defect, and did not fix this.

The actual cause is in the test harness, not the application: the worker is started with
`stdout=subprocess.PIPE` and **nothing ever reads it**. Once the OS pipe buffer fills, the child blocks
forever on its next write — mid-task, with no error and no further output. Windows pipe buffers are far
smaller than macOS/Linux ones, so the same log volume that fits on a developer's machine overflows there.

## Acceptance Criteria

1. **The worker's output is drained continuously**, for the worker's whole life rather than only during boot.
2. **The failure dump still works** — it reads the accumulated buffer instead of the pipe.
3. **The registry test reads the same buffer**, not the raw stream.
4. **A phase logs on entry**, so "received then silence" localizes to a phase rather than a task.
5. **Gate green**, and the test passes with the Windows worker configuration (`FORCE_SOLO=1`).

## Tasks / Subtasks

- [x] **Task 1 — Reproduce it off Windows (AC: all)** — raise the worker's log level and watch it hang
- [x] **Task 2 — `_Worker`: a reader thread for the process's whole life (AC: #1, #2, #3)**
- [x] **Task 3 — `phase_<type>_started` entry log (AC: #4)**
- [x] **Task 4 — Gate (AC: #5)**

## Dev Notes

### The investigation, in the order it actually went

1. **`--pool=solo` deadlocks the analysis chord** — *falsified*. Added `FORCE_SOLO=1` to run the Windows
   worker configuration anywhere; it passed on macOS in ten seconds.
2. **Break the TLS trust store to force the analysis phases offline** — *rejected*. It fails Phase 1, not
   just the analysis phases, so the job dies rather than degrades.
3. **No HTTP timeout** (Story 22.15) — *a real defect, fixed on its own merits, and not this one.*
   `requests` has no default timeout and Celery's soft time limit needs a signal Windows lacks. Windows
   still failed identically afterwards.
4. **The pipe was never drained** — *confirmed*, by raising the worker to `--loglevel=DEBUG` and watching
   the test hang **on macOS** at exactly `progress=45`. 216 seconds, same symptom, on a machine where it
   had always passed.

The thing that finally worked was making the failure louder rather than reasoning harder about it. Step 4
was a one-line change that turned a platform-specific mystery into a local reproduction.

### Why this looked like an application bug for so long

Every symptom pointed inward: a task received and never completing, no reports written, a job stuck at 45%.
The worker log stopping was read as *the worker stopped doing things*, when it actually meant *the worker
could no longer say what it was doing* — and those are indistinguishable from outside if the log is the only
instrument.

### Traps

- **`stdout=PIPE` without a reader is a latent deadlock in any subprocess test**, not just this one. It is
  invisible until the child is chatty enough or the buffer small enough.
- **Do not "fix" it by lowering the log level.** That restores the old margin without removing the trap; the
  next added log line brings it back, on someone else's platform.
- **`bufsize=1` (line buffered)** pairs with the reader thread; leaving it default works but delays lines.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- **Reproduction:** `--loglevel=DEBUG` + `FORCE_SOLO=1` on macOS → hang, `status=PROGRESS progress=45
  reports=[]`, **216s**.
- **After the fix:** same command, **14.8s**, both tests pass — with *more* logging than the configuration
  that used to hang.
- `pixi run ci` — **exit 0**, 927 tests, 97.23%.

### Completion Notes List

**The 216-second run is the proof.** It is the same assertion failure Windows produced, on a machine where
the test had passed a dozen times, produced by nothing but raising the log level — which is what identifies
the buffer rather than the network, the pool, or the platform.

**The log level stays at DEBUG.** With the pipe drained it costs nothing, and this test has only ever failed
on a platform the author cannot attach a debugger to, so the log is the debugger.

**Story 22.15 stands on its own.** Missing HTTP timeouts were a real defect — an unanswered connection would
still hang a worker in production, where nothing is draining anything. It simply was not *this* defect.

**The entry log is the part that generalizes.** `phase_<type>_started` is logged before `update_state` and
before the job is loaded, so a phase that blocks in either now says so. Without it the worker log stops at
Celery's own "Task … received", which is where three investigations began with nothing.

### File List

**Modified (2)**
- `tests/integration/test_real_worker_pipeline.py` — `_Worker` reader thread, `--loglevel=DEBUG`
- `src/django_apps/inventory/tasks/analysis.py` — `phase_<type>_started` entry log

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Fixed the real-worker test's Windows failure, after three earlier attempts. The worker was started with `stdout=PIPE` and nothing ever read it, so once the pipe buffer filled the process blocked forever on its next write — mid-task, silently. Windows buffers are much smaller, which is why only Windows hit it. Confirmed by raising the log level and reproducing the identical hang on macOS (216s), then fixed with a reader thread that drains for the worker's whole life (14.8s, with more logging than before). Added a phase entry log so "received then silence" localizes to a phase next time. |
