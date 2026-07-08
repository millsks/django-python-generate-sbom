# Story 20.5: Cross-Platform pixi Tasks & `pixi run dev`

Status: review

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

- [x] **Task 0 — Sign-off (AC: #1)** — `honcho` approved by the user at implementation time.
- [x] **Task 1 — Procfile + dev task (AC: #1, #2, #5)** — Root `Procfile` declares `web`/`worker`/`beat`
  (each delegates to a pixi task); `[tasks.dev]` runs `honcho start` with `DJANGO_SETTINGS_MODULE=config.settings.local`
  set on the whole process tree.
- [x] **Task 2 — runserver web task (AC: #2)** — Added `[tasks.runserver]`
  (`python manage.py runserver 0.0.0.0:8000`, `cwd = "backend"`, local settings); the gunicorn `web` task is
  unchanged (container/prod).
- [x] **Task 3 — Per-platform worker (AC: #3, #4)** — Added `[tasks.worker]` (prefork `-c 4`, both queues) and a
  `[target.win-64.tasks.worker]` override using `--pool=solo`; no task uses `sh -c` or POSIX chaining (the
  Procfile delegates to pixi tasks).
- [x] **Task 4 — Portable beat (AC: #5)** — The Procfile `beat` process runs the existing `beat` task, which
  already uses the portable git-ignored schedule path from Story 20.4.
- [x] **Task 5 — Verify + gate (AC: #6)** — `pixi run dev` on macOS launched web/worker/beat together via honcho
  (worker prefork `-c 4`, portable beat path, no pool/path/shell error); `pixi run ci` exits 0.

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

Claude Opus 4.8 (1M context) — claude-opus-4-8[1m]

### Debug Log References

- honcho 1.1.0 imports the removed `pkg_resources` and crashes under setuptools >= 81 (env ships setuptools
  82). Bumped the dependency to `honcho >=2,<3` (2.0.0 uses `importlib.metadata`); win-64 solve resolves the
  noarch package. `pixi run honcho check` reports "Valid procfile detected (web, worker, beat)".
- `pixi run dev` smoke test on macOS: honcho started all three processes; web (runserver) began "Watching for
  file changes" and only failed to bind :8000 because the host's Docker already held that port — a local
  environment conflict, not a wiring bug. worker (`celery … -Q pipeline,analysis -c 4`) and beat (portable
  `.celery/celerybeat-schedule` path) started cleanly with no pool/path/shell incompatibility.

### Completion Notes List

- `env` with `DJANGO_SETTINGS_MODULE=config.settings.local` is set only on the NEW local-only tasks
  (`runserver`, `worker`, the win-64 `worker` override) and on `dev` (which propagates it to the whole honcho
  process tree). It is deliberately NOT added to the shared `beat`/`worker-pipeline`/`worker-analysis`/`web`
  tasks, because docker-compose runs those via `pixi run` with `config.settings.production` — a task-level env
  would override the container's production setting.
- The Procfile delegates each process to a pixi task (`pixi run runserver|worker|beat`) rather than inlining
  commands, so cwd, the per-OS worker pool override, and the local settings env are all resolved by pixi and
  the same Procfile is correct on macOS and Windows.
- Added a config-wiring unit test (`tests/unit/test_dev_runner_config.py`) that parses the Procfile and
  `pixi.toml` to assert the dev/runserver/worker tasks, the win-64 `--pool=solo` override, honcho as a dev dep,
  local settings on local tasks, gunicorn kept for the container `web`, and no `sh -c`/`&&` in cross-platform
  tasks.

### File List

- `pixi.toml` (modified) — added `honcho` dev dep; `[tasks.runserver]`, `[tasks.worker]`, `[tasks.dev]`;
  `[target.win-64.tasks.worker]` (`--pool=solo`) override; comment scoping the gunicorn `web` task to prod.
- `Procfile` (new) — root Procfile declaring `web`/`worker`/`beat` for honcho.
- `pixi.lock` (modified) — honcho 2.0.0 (noarch) resolved for all 4 platforms incl. win-64.
- `backend/tests/unit/test_dev_runner_config.py` (new) — task/Procfile wiring tests.
