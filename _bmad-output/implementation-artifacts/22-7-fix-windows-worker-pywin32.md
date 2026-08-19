---
baseline_commit: f4e3f7f
---

# Story 22.7: Fix the Celery Worker Failing to Start on Windows

Status: review

> **Written after implementation** and backfilled on 2026-08-18; see the note in Story 22.5.

> **This is a bug fix, so the branch prefix is `bugfix/` and the commit type is `fix:`** (global
> standards §5). It shipped on the Epic 22 branch with the other stories at the product owner's request.

## Story

As a developer on Windows,
I want the containerless Celery worker to start,
so that background jobs run at all on the platform that has no Docker fallback.

**Context:** Found by Story 22.4's real-worker test on its **first** run against `windows-latest`, and
**shipping broken since Epic 20**. Kombu's `filesystem://` transport locks its message files with
`LockFileEx`, so `kombu/transport/filesystem.py` unconditionally imports `pywintypes`, `win32con`, and
`win32file` under `os.name == "nt"`. `pywin32` was never declared, so `pixi run worker`, `pixi run beat`,
and therefore `pixi run dev` all died at import with `ModuleNotFoundError`.

**Nothing could have caught this earlier.** Story 20.6's Windows job ran unit tests only, and those use
eager Celery, which never loads the transport. This is the second real defect the Epic 22 hardening
surfaced — which is the argument for the epic.

## Acceptance Criteria

1. **The worker starts on Windows**, and Story 22.4's end-to-end test passes on `windows-latest`.
2. **The dependency is scoped to the platform that needs it** — `[target.win-64.dependencies]` only, absent
   from every other platform's resolved environment.
3. **It cannot be dropped silently** — a test asserts the win-64 declaration exists, with the reason beside it.

## Tasks / Subtasks

- [x] **Task 1 — Declare `pywin32` under `[target.win-64.dependencies]` (AC: #1, #2)**
- [x] **Task 2 — Guard it (AC: #3)** — two tests: the declaration exists, **and** it is not installed on
      every platform, so a careless move to `[dependencies]` fails.
- [x] **Task 3 — Gate**

## Dev Notes

### Why this needed a new runtime dependency

`pywin32` is a genuine runtime requirement of the broker on Windows, not a dev convenience. It was added
with explicit user authorisation (*"please do it so the product works correctly"*), per global standards §7.

### Traps

- **The failure is invisible on macOS and Linux.** Both tests matter: asserting only that the declaration
  exists would still pass if someone moved it to the shared `[dependencies]` table, which would then try to
  resolve `pywin32` on osx-arm64.
- **Unit tests cannot catch this class of bug at all** — eager Celery never loads a transport. Only the
  real-worker integration test from Story 22.4 exercises it.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**; `pixi.lock` re-resolved (win-64 only).
- 2 new tests in `tests/unit/test_cross_platform_portability.py`.

### Completion Notes List

**Found by a test written the day before.** Story 22.4 added the first real-worker end-to-end test and the
first full Windows gate; this defect surfaced on that job's first run. It had been shipping to every
Windows developer since Epic 20 — on the one platform with no container fallback, there was no working
background-job path at all.

**The reason is recorded beside the declaration**, including kombu's own comment (*"needs win32all to work
on Windows"*), because a platform-scoped dependency with no explanation is the kind of line someone removes
while tidying.

### File List

**Modified (6)**
- `pixi.toml` — `[target.win-64.dependencies] pywin32 = ">=306"`, with the reason
- `pixi.lock` — re-resolved
- `src/config/settings/local.py` — `CELERY_DIR` made env-overridable
- `tests/unit/test_cross_platform_portability.py` — 2 tests
- `tests/integration/test_real_worker_pipeline.py`
- `_bmad-output/planning-artifacts/epics.md`, `sprint-status.yaml`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Declared `pywin32` under `[target.win-64.dependencies]` so kombu's `filesystem://` transport can import `LockFileEx` and the Celery worker, beat, and `pixi run dev` start on Windows. Broken since Epic 20 and invisible to unit tests, which run eager Celery and never load a transport; found by Story 22.4's real-worker job on its first Windows run. Guarded by two tests — the declaration exists, and it stays off every other platform. |
