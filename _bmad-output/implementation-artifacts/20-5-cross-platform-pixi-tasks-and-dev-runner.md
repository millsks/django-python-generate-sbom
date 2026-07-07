# Story 20.5: Cross-Platform pixi Tasks & `pixi run dev`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 20.4** (it defines the per-OS worker pool and the portable beat path this
> story wires into pixi tasks).

> **⚠ SIGN-OFF GATE.** This story **proposes a new dev dependency — `honcho`** (a pure-Python, cross-platform
> Procfile runner). Adding a dependency requires the **user's explicit sign-off at implementation time**
> (Control Constraints §7). The story proposes; do not add the dep until the user approves.

## Story

As a developer,
I want a single `pixi run dev` that launches web + worker + beat together on macOS or Windows,
so that I can run the whole containerless stack with one command and no Docker.

## Acceptance Criteria

1. **A committed Procfile + honcho launch web/worker/beat (SIGN-OFF).**
   Given there is **no Procfile and no honcho** in the repo today, when the user approves `honcho`, then a
   root `Procfile` declares the local processes — `web` (`runserver`), `worker` (the pipeline+analysis Celery
   worker), and `beat` — and a `pixi run dev` task runs `honcho start` against it, launching all three in one
   foreground command that works identically on macOS and Windows. **If sign-off is withheld, this story stops
   at the proposal** (documenting the manual multi-terminal fallback).
2. **Local web uses `runserver`, not gunicorn.**
   Given the `web` task is `gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 4` (`pixi.toml` L138–140) and
   gunicorn is Unix-only, when local dev runs, then the Procfile/`dev` web process uses
   `python manage.py runserver 0.0.0.0:8000` (cross-platform) under `DJANGO_SETTINGS_MODULE=config.settings.local`
   — and the existing `gunicorn` `web` task is **kept, scoped to containers/prod only** (unchanged for the
   Dockerfile/OCP path).
3. **Per-platform task overrides where shell/pool differ.**
   Given the Celery prefork pool is Unix-only, when the worker task runs, then a
   **`[target.win-64.tasks]`** override runs the worker with `--pool=solo` (or `threads`) while the default
   (macOS/Linux) worker keeps prefork `-c 4` — the Windows worker pool is set via the target override, not a
   shared command.
4. **No Unix-only shell in cross-platform tasks.**
   Given docker-compose bundles commands with `sh -c "…"`, when the cross-platform local tasks are authored,
   then they avoid `sh -c`, `&&` chaining that relies on a POSIX shell, and any Unix-only path/quoting — each
   task is a single portable invocation (chaining, where needed, is expressed via pixi `depends-on`, not a
   shell operator).
5. **Portable beat + settings wired.**
   Given Story 20.4's portable beat schedule path and local settings, when the `dev`/beat task runs, then beat
   uses the portable git-ignored schedule path (not `/tmp`) and every local task sets
   `DJANGO_SETTINGS_MODULE=config.settings.local` (via a task `env` or the pixi `[activation]`/task env) so no
   process falls back to the production-defaulting `wsgi`/`asgi`.
6. **`pixi run dev` verified on both OSes + gate green.**
   Given the wiring, when `pixi run dev` runs on macOS and on Windows, then web serves on `:8000`, a real
   worker drains a submitted job, beat starts against the portable schedule, and no process fails on a
   pool/path/shell incompatibility; `pixi run ci` (lint/check/test) stays green.

## Tasks / Subtasks

- [ ] **Task 0 — Sign-off (AC: #1)** — Propose `honcho` to the user; do not add it to `pixi.toml` until
  approved.
- [ ] **Task 1 — Procfile + dev task (AC: #1, #2, #5)** — After sign-off: add a root `Procfile` with
  `web`/`worker`/`beat` lines (web = `runserver`); add a `[tasks.dev]` running `honcho start`; set
  `DJANGO_SETTINGS_MODULE=config.settings.local` for the local tasks.
- [ ] **Task 2 — runserver web task (AC: #2)** — Add a `runserver` pixi task
  (`python manage.py runserver 0.0.0.0:8000`, `cwd = "backend"`); keep the gunicorn `web` task unchanged
  (container/prod).
- [ ] **Task 3 — Per-platform worker (AC: #3, #4)** — Add `[target.win-64.tasks]` worker override using
  `--pool=solo`/`threads`; keep the default worker at prefork `-c 4`; ensure no task uses `sh -c` or POSIX-only
  chaining (use `depends-on`).
- [ ] **Task 4 — Portable beat (AC: #5)** — Point the local beat task at the portable schedule path from
  Story 20.4.
- [ ] **Task 5 — Verify + gate (AC: #6)** — Run `pixi run dev` on macOS (and Windows where available);
  confirm web/worker/beat come up and a job drains; run `pixi run ci` to green.

## Dev Notes

### Grounded facts (verified)

- `pixi.toml`: `web` = `gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 4` (L138–140, Unix-only);
  `worker-pipeline` = `celery … worker -Q pipeline -c 4` (L142–144); `worker-analysis` = `… -Q analysis -c 4`
  (L146–148); `beat` = `celery … beat -s /tmp/celerybeat-schedule` (L150–152). **No `runserver` task, no
  `dev` task**; the only combined-run path today is docker-compose. No `[target.*]` tables exist yet.
- **No Procfile, no honcho** anywhere in the repo (verified).
- `manage.py` defaults `DJANGO_SETTINGS_MODULE=config.settings.local` (L10) — `runserver` picks it up without
  extra env, but set it explicitly on the tasks for clarity and to override any inherited value.

### Worker consolidation for local dev

Locally, a single `worker` process consuming **both** the `pipeline` and `analysis` queues is sufficient (one
process instead of two), e.g. `celery -A config.celery_app worker -Q pipeline,analysis`. Production keeps the
two dedicated `worker-pipeline`/`worker-analysis` tasks. Confirm with the pipeline's queue routing that a
single multi-queue worker drains both.

### Windows specifics

- Celery prefork is Unix-only → `--pool=solo` (single-threaded, simplest and reliable for local dev) or
  `threads` on `win-64`, via `[target.win-64.tasks]`.
- gunicorn is Unix-only → Windows (and cross-platform local) uses `runserver`.
- honcho is pure-Python and cross-platform (unlike `foreman`); it reads the same `Procfile` on both OSes.
- Avoid `sh -c` — pixi tasks run in a cross-platform manner, but a `sh -c "a && b"` command assumes a POSIX
  shell absent on Windows. Use pixi `depends-on` for ordering.

### Testing standards

- No unit-test surface for task wiring — verification is running `pixi run dev` on each OS and confirming the
  three processes start and a job drains. The `pixi.toml`/`Procfile` diff is the reviewable artifact; the
  existing `pixi run ci` (lint/check/test) must stay green.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.5: Cross-Platform pixi Tasks & `pixi run dev`]
- `pixi.toml` (L138–152 tasks; add `[tasks.dev]`, `[tasks.runserver]`, `[target.win-64.tasks]`), new root
  `Procfile`, `backend/manage.py` (L10).
- Upstream: `20-4-cross-platform-async-worker.md` (per-OS pool + portable beat path),
  `20-2-add-win-64-platform-and-verify-env.md` (gunicorn scoped off win-64).
- Downstream: `20-7-docs-cross-platform-local-dev.md` (documents `pixi run dev`).

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
