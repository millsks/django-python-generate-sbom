# Story 20.8: Frontend Local Dev Loop (`pixi run dev` serves a hot-reloading UI)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Reopens Epic 20 (dev-loop).** Epic 20 delivered the containerless backend loop
> (`pixi run dev` = `runserver` + worker + beat via honcho/Procfile) but left the
> **frontend** out: there is no `pixi run fe-dev` task, `vite.config.ts` has no dev
> proxy, and a fresh `pixi install → pixi run dev` serves the API but **no UI**.
> This story closes that gap. No new dependency — Vite/npm are already present.

## Story

As a developer,
I want `pixi run dev` to also bring up a hot-reloading frontend that proxies to the backend,
so that a fresh `pixi install → pixi run dev` serves a working UI, not just the API.

## Acceptance Criteria

1. **`pixi run fe-dev` runs the Vite dev server.**
   **Given** the frontend has a `"dev": "vite"` script but no pixi task wraps it,
   **When** a developer runs `pixi run fe-dev`,
   **Then** a `[tasks.fe-dev]` task (`cmd = "npm run dev"`, `cwd = "frontend"`,
   `depends-on = ["fe-install"]`, mirroring the other `fe-*` tasks) starts the Vite
   HMR dev server on the default port `:5173`.

2. **Vite dev proxy forwards API calls to Django.**
   **Given** the SPA API client issues relative `/api/...` requests (`src/api/client.ts`)
   and the dev server is a separate origin from Django,
   **When** the dev server runs,
   **Then** `vite.config.ts` defines `server.proxy` forwarding `/api` (and `/admin`,
   `/static` for the DRF browsable API / Swagger + admin) to `http://localhost:8000`,
   so the SPA's API calls reach the real backend through the proxy.

3. **The production build is unchanged.**
   **Given** the built SPA is served by WhiteNoise under `/static/` (AD-5),
   **When** `vite build` runs,
   **Then** `base` is `'/static/'` only for the production **build** (`command === 'build'`)
   and `'/'` for the **dev server** — `pixi run fe-build` still emits `/static/`-based
   asset URLs into `frontend/dist/`, unchanged from before this story.

4. **`pixi run dev` brings the frontend up with the backend.**
   **Given** the root `Procfile` declares `web`/`worker`/`beat`,
   **When** `pixi run dev` runs,
   **Then** the Procfile also declares a `frontend` process (`pixi run fe-dev`), so one
   command starts web (API `:8000`) + worker + beat + frontend (HMR `:5173`); the UI is
   reachable at **http://localhost:5173** and its `/api` calls proxy to Django on `:8000`.

5. **Docs cover the frontend dev loop.**
   **Given** `docs/developer/setup.md` previously claimed the frontend dev server runs
   through `fe-*` tasks (none existed),
   **When** this story lands,
   **Then** the docs document the frontend loop (`pixi run dev` also starts Vite HMR;
   the UI is at `http://localhost:5173`; `pixi run fe-dev` runs it alone), fix the
   inaccurate `fe-*` dev-server line, add a **`:8000` port-conflict warning** (the Docker
   Compose stack and `pixi run dev` both bind `:8000` — stop one first), and note the
   loop is cross-platform via the pixi Node runtime.

6. **Contract test + gate green.**
   **Given** the Procfile/task contract is the reviewable artifact,
   **When** the wiring lands,
   **Then** `backend/tests/unit/test_dev_runner_config.py` asserts the new `frontend`
   Procfile process and the `fe-dev` task, and `pixi run ci` exits 0 (incl. `fe-build`
   output unchanged, `fe-typecheck`, `docs-build --strict`, and the win-64 solve
   unaffected).

## Tasks / Subtasks

- [x] **Task 1 — `fe-dev` task (AC: #1)** — Added `[tasks.fe-dev]` (`npm run dev`,
  `cwd = "frontend"`, `depends-on = ["fe-install"]`).
- [x] **Task 2 — Vite dev proxy + command-aware base (AC: #2, #3)** — Switched
  `vite.config.ts` to `defineConfig(({ command }) => ...)`: `base` = `'/static/'` for
  `build`, `'/'` otherwise; added `server.proxy` for `/api`, `/admin`, `/static` →
  `http://localhost:8000`. `pixi run fe-build` output unchanged.
- [x] **Task 3 — Procfile integration (AC: #4)** — Added a `frontend: pixi run fe-dev`
  process line to the root `Procfile`.
- [x] **Task 4 — Tests (AC: #6)** — Added `test_procfile_declares_frontend_process` and
  `test_fe_dev_task_runs_vite` to `test_dev_runner_config.py`; relaxed the "exactly three"
  wording on the existing web/worker/beat assertion (now a subset check).
- [x] **Task 5 — Docs (AC: #5)** — Updated `docs/developer/setup.md`: 4-process table,
  `:5173` UI callout, `:8000` port-conflict warning, `pixi run fe-dev` in the
  individual-pieces + everyday-tasks lists, a Windows-specifics bullet, and fixed the
  inaccurate `fe-*` line.
- [x] **Task 6 — Gate (AC: #6)** — `pixi run ci` exits 0.

## Dev Notes

### Grounded facts (verified)

- `frontend/package.json` has `"dev": "vite"` but no pixi task wrapped it. Existing fe
  tasks: `fe-install/lint/build/test/typecheck/security/cov` (`pixi.toml`).
- `frontend/vite.config.ts` was `defineConfig({ base: '/static/', plugins: [react()] })`
  — tuned for the WhiteNoise-served build, **no `server.proxy`**.
- Backend serves the SPA from `frontend/dist` only if it exists
  (`config/settings/base.py` `FRONTEND_DIST`/`STATICFILES_DIRS`/`SPA_INDEX_FILE`).
- `pixi run dev` = honcho over the root `Procfile` (`web`=runserver:8000, `worker`, `beat`);
  `env` sets `DJANGO_SETTINGS_MODULE=config.settings.local`.
- SPA API client base is `/api/v1` (`src/api/client.ts`) — relative, so the `/api` proxy
  prefix covers it.

### Design decisions

- **Command-aware config, not a mode/env split.** `command === 'build'` cleanly separates
  the WhiteNoise `/static/` build base from the dev-server `/` base without a `.env` file
  or `mode` plumbing.
- **Proxy `/static` too.** In dev the SPA base is `/`, so Vite serves its own module
  assets at `/`; proxying `/static` therefore safely forwards only Django's DRF-browsable
  / Swagger / admin static assets to `:8000`.
- **No new dependency.** Vite and npm already ship with the frontend; `fe-dev` just wraps
  the existing `npm run dev` script, so no sign-off gate applies.
- **Vitest untouched.** Test config lives in `vitest.config.ts` (separate from
  `vite.config.ts`), so the command-aware change does not affect `fe-test`/`fe-cov`.

### Testing standards

- Contract test only (the Procfile/`pixi.toml` diff is the reviewable artifact) — mirrors
  Story 20.5's `test_dev_runner_config.py`. Runtime proxy behavior is verified by running
  `pixi run dev` and loading `http://localhost:5173` (UI) with its `/api` calls reaching
  Django on `:8000`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 20: Unified Cross-Platform Local Development (containerless)]
- `pixi.toml` (`[tasks.fe-dev]`), root `Procfile` (`frontend` process),
  `frontend/vite.config.ts` (command-aware base + `server.proxy`),
  `docs/developer/setup.md`, `backend/tests/unit/test_dev_runner_config.py`.
- Upstream: `20-5-cross-platform-pixi-tasks-and-dev-runner.md` (the honcho/Procfile loop),
  `20-7-docs-cross-platform-local-dev.md` (the setup docs this extends).

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (1M context) — claude-opus-4-8[1m]

### Completion Notes

- `fe-dev` task, Vite dev proxy, and the `frontend` Procfile process wired; `pixi run dev`
  now serves a hot-reloading UI at `:5173` proxying `/api` to Django on `:8000`.
- `pixi run fe-build` output confirmed unchanged (asset URLs stay `/static/`-based).
- `pixi run ci` exits 0.
