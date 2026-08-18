---
baseline_commit: d8ab00a
---

# Story 21.19: Retire the React SPA and the Node Toolchain

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.18**. **Nothing here may start until every route has a Django owner**
> (Stories 21.5–21.18) and the server-side Excel export exists (21.17). This is the story that makes the
> epic's benefit real.

## Story

As a developer,
I want the React application and every trace of its build chain removed,
so that the project has one language and one toolchain.

## Acceptance Criteria

1. **The SPA and Node leave the toolchain.**
   Given `frontend/` holds 4,578 non-test lines, 39 vitest files, and a `node_modules` tree, when the SPA is
   retired, then the entire `frontend/` directory is deleted, and `pixi.toml` drops `nodejs = ">=20"` (`:18`)
   and all eight `fe-*` tasks (`fe-install`, `fe-dev`, `fe-lint`, `fe-build`, `fe-test`, `fe-typecheck`,
   `fe-security`, `fe-cov`).
2. **The AD-5 coupling is removed with no route left behind.**
   Given Django serves the SPA entrypoint through a catch-all, when the coupling is removed, then `SpaView`,
   the `re_path(r"^(?!api/|health/|static/|admin/).*$")` catch-all (`backend/config/urls.py:38`),
   `SPA_INDEX_FILE`, and the `FRONTEND_DIST`/`STATICFILES_DIRS` block (`base.py:145-147`) are all deleted, and
   **no path that previously reached a SPA route now 404s** — each resolves to its Django view.
3. **Build and process definitions are cleaned.**
   Given the container build and dev runner reference the frontend, when they are cleaned, then `Dockerfile`
   drops `COPY frontend/` and the `pixi run fe-build` step (keeping `collectstatic`), and the `frontend:` line
   leaves `Procfile` — reversing Story 20.8.
4. **CI drops the frontend jobs.**
   Given `ci.yml` runs `frontend-quality` (`:75`), `frontend-test` (`:90`), and `frontend-build` (`:126`), when
   CI is cleaned, then those three jobs are removed along with their entries in the `needs:` arrays (`:143`,
   `:164`) and the frontend half of the Windows job (`:201`), and `maintenance.yml` drops the `fe-security`
   npm audit (`:48`).
5. **Coverage and quality tooling become Python-only.**
   Given two source trees are reported today, when they are cleaned, then `codecov.yml` drops the `frontend`
   flag and component, and `sonar-project.properties` drops all six frontend references (`:21`, `:22`, `:29`,
   `:30`, `:33`, `:43`).
6. **A clean checkout needs no Node.**
   Given the whole point is a simpler toolchain, when the story completes, then a clean checkout requires **no
   Node runtime** to build, test, or run the application, `pixi run ci` exits 0, and `pixi run dev` starts web
   + worker + beat with the UI reachable at `:8000`.

## Tasks / Subtasks

- [x] **Task 0 — Confirm prerequisites** — Every route from `App.tsx` has a Django owner; Story 21.17's
  reference workbooks are committed. Do not proceed otherwise.
- [x] **Task 1 — Delete `frontend/` (AC: #1)**.
- [x] **Task 2 — pixi cleanup (AC: #1)** — `nodejs` dependency and the eight `fe-*` tasks; check the `ci` task's
  `depends-on` array for `fe-*` entries.
- [x] **Task 3 — Remove the SPA coupling (AC: #2)** — `SpaView`, catch-all, `SPA_INDEX_FILE`, `FRONTEND_DIST`,
  `STATICFILES_DIRS`.
- [x] **Task 4 — Dockerfile + Procfile (AC: #3)**.
- [x] **Task 5 — CI + maintenance workflows (AC: #4)**.
- [x] **Task 6 — Codecov + Sonar (AC: #5)**.
- [x] **Task 7 — Clean-checkout verification (AC: #6)** — Fresh clone, `pixi install`, `pixi run ci`,
  `pixi run dev`, walk every route.

## Dev Notes

### Grounded facts (verified)

- `pixi.toml:18` — `nodejs = ">=20"`; `:279-327` — the eight `fe-*` tasks, each `cwd = "frontend"` with
  `depends-on = ["fe-install"]`; `:333` — the `ci` task's `depends-on` array (check it for `fe-*` members).
- `Dockerfile` — `COPY frontend/ frontend/` then `RUN pixi run fe-build && … collectstatic`.
- `Procfile` — `frontend: pixi run fe-dev` (Story 20.8), with the comment that it proxies `/api` to web on
  `:8000`.
- `backend/config/urls.py:38` — the catch-all, with the standing comment "The SPA catch-all must remain last so
  it never shadows the routes above."
- `backend/generate_sbom/common/views.py` — `SpaView`, whose 404 body is literally
  "SPA not built. Run: pixi run fe-build".
- `backend/config/settings/base.py:143-147` — `FRONTEND_DIST`, `STATICFILES_DIRS`, `SPA_INDEX_FILE`.
- `.github/workflows/ci.yml` — `frontend-quality` `:75`, `frontend-test` `:90`, `frontend-build` `:126`,
  `needs:` at `:143` and `:164`, Windows job `:201`; `maintenance.yml:48` — `fe-security`.
- `codecov.yml` — `frontend` flag (`:21-25`, `:38-40`) and component (`:49-52`).
- `sonar-project.properties` — `:21`, `:22`, `:29`, `:30`, `:33`, `:43`.

### AC #2 is the one that bites

Deleting the catch-all converts every un-migrated path from "renders the SPA" to "404". That is the intended
outcome, but it means a route missed in Stories 21.5–21.18 fails **only at this point**. Enumerate the ten
routes from `App.tsx` and walk each one before deleting `SpaView`.

### Watch for

- **`STATICFILES_DIRS` becomes `[]` or is removed** — but Story 21.3 added `APPS_DIR / "static"` to it. Remove
  only the `FRONTEND_DIST` entry, not the whole setting.
- **The `ci` pixi task's `depends-on`** almost certainly lists `fe-*` tasks; a stale reference breaks the gate.
- **The Windows CI job** runs both suites; remove only the frontend half, keeping the Python coverage the
  `win-64` job exists for (Story 20.6).
- **Do not delete `frontend/` before Story 21.17's reference workbooks are committed** — they cannot be
  regenerated afterwards.

### Testing standards

- A test asserting no settings key references `frontend`.
- A routing test that walks all ten original SPA paths and asserts each resolves to a Django view.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.19: Retire the React SPA and the Node Toolchain]
- `frontend/**`, `pixi.toml`, `Dockerfile`, `Procfile`, `backend/config/urls.py`,
  `backend/generate_sbom/common/views.py`, `backend/config/settings/base.py`,
  `.github/workflows/{ci,maintenance}.yml`, `codecov.yml`, `sonar-project.properties`.
- Upstream: `21-18-landing-page-and-visual-identity.md`, `21-17-server-side-excel-export.md`.
- Architecture: AD-5 (retired here, formally superseded in Story 21.20), AD-13 (amended).

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. **806 passed**, coverage **96.72%**. No frontend step remains in
  the gate.
- **Clean-checkout verification (AC #6):** a fresh tree, `pixi install --locked` → succeeds;
  `.pixi/envs/default/bin/node` and `npm` **absent**; `pixi run test` → **798 passed**.
- `pixi.lock` re-solved with **zero** `nodejs` references.
- **`pixi run dev` (AC #6):** honcho starts **web + worker + beat** — three processes, no
  frontend. Route walk against `:8000`: `/` 200, `/register` 200, `/login` 200, and
  `/organization` `/members` `/keys` `/upload` `/history` `/platform/global-admins` all 302 to
  login (owned, not 404). `/health/` 200, `/admin/` 302, `/definitely-not-real` **404**.
  `/static/css/bootstrap.min.css` and `/static/images/icons.svg` both 200.
- **13 new tests** in `tests/unit/test_spa_retirement.py`; `test_spa.py` and
  `test_manifest_format_consistency.py` deleted.

### Completion Notes List

**Task 0 was run as a test, before anything was deleted.** The Dev Notes call AC #2 "the one
that bites": deleting the catch-all converts every un-migrated path from *renders the SPA* to
*404*, so a route missed in Stories 21.5-21.18 fails only at this point. So the ten routes were
transcribed out of `App.tsx`'s `<Route>` table into a parametrised test and run **while the SPA
was still in place** — all ten resolved and all ten answered non-404. Only then was `frontend/`
deleted. That transcription is also the reason the test still means something now that
`App.tsx` no longer exists to check against.

**One route needed a real job to be checked honestly.** `/results/<placeholder-id>` 404s
correctly — AD-2 makes a cross-org job indistinguishable from a missing one — so a placeholder
id cannot tell *"the route lost its owner"* from *"that job does not exist"*, which is precisely
the confusion this story's tests exist to avoid. The test creates a job the requesting org owns.

**The `*`-fallback decision from Story 21.18 is implemented here, as promised.** An unknown path
now 404s instead of answering 200 with the landing page. 21.18's
`test_an_unknown_path_still_falls_back_to_the_spa` said in its docstring that this story was
expected to replace it; it is now `test_an_unknown_path_now_404s` in the retirement module, with
a pointer left behind at the old site. The behaviour change is in the diff of the story that
owns it rather than buried in the one before.

**The removal checks are file-level on purpose.** A half-removal is the likely failure here, and
none of it is behavioural: a stale `fe-*` entry in the `ci` task's `depends-on`, a lingering
`frontend` flag in `codecov.yml`, a `COPY frontend/` in the `Dockerfile`. No test of the
application would ever notice. So there is a parametrised test asserting none of the six build
and CI files mentions `frontend`, `npm`, `node_modules`, or any `fe-*` task, plus one that walks
every pixi task's `depends-on` and fails on a reference to a task that no longer exists — a stale
entry there breaks the gate itself.

**`STATICFILES_DIRS` was pruned, not emptied.** The Dev Notes flagged this: Story 21.3 put the
vendored Bootstrap/htmx assets and the icon sprite in the same setting the SPA bundle used.
Only the `FRONTEND_DIST` entry went, and a test asserts the list is still non-empty — emptying it
would have 404'd every stylesheet, which the live route walk confirms it does not.

**The Windows job kept the half it exists for.** Story 20.6 added `unit-windows` to catch POSIX
paths, the Unix-only Celery prefork pool, and gunicorn imports. Only its `fe-test` step went.

**Two test modules were deleted, for different reasons, and one claim was rescued.**
`test_spa.py` tested `SpaView` and the catch-all — both gone. But one of its assertions was that
the admin site is not shadowed, and *that* is worth keeping independently of what used to
threaten it, so it moved into the retirement module with a note saying where it came from.
`test_manifest_format_consistency.py` existed to keep a TypeScript constant in step with the
Django enum (Story 6.4 AC #4); with no TypeScript constant there is nothing left to drift, so
deleting it is correct rather than a coverage loss.

**One Procfile test was inverted rather than deleted.** A leftover `frontend:` line would make
honcho try to start a task that no longer exists, failing `pixi run dev` at the moment a
developer is least expecting it — so the test now asserts the Procfile declares *no* frontend
process and no `fe-` command at all.

**The lock file re-solved rather than being hand-edited**, and the clean checkout is the proof
that matters: `pixi install --locked` in a fresh tree produces an environment with no `node` and
no `npm` binary, and the suite passes in it. That is AC #6 demonstrated rather than asserted.

**Not done here, and deliberately.** `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and seven
pages under `docs/` still describe the React SPA. That is Story 21.21's scope (documentation
reconciliation), which the epic sequences after this one precisely so the docs describe the UI
that exists rather than the one being built. AD-5 is retired in behaviour here and formally
superseded in Story 21.20.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**Deleted**
- `frontend/` — the entire SPA tree (4,578 non-test lines, 39 vitest files, `node_modules`)
- `tests/unit/test_spa.py`, `tests/unit/test_manifest_format_consistency.py`

**New (1)**
- `tests/unit/test_spa_retirement.py` (13 tests, 34 cases with parametrisation)

**Modified (12)**
- `pixi.toml` / `pixi.lock` — `nodejs` and the eight `fe-*` tasks removed; four `fe-*` entries
  dropped from the `ci` task's `depends-on`
- `Procfile` — the Vite line removed (reverses Story 20.8)
- `Dockerfile` — `COPY frontend/` and the `fe-build` step removed; `collectstatic` kept
- `src/config/urls.py` — the SPA catch-all removed
- `src/django_apps/inventory/common/views.py` — `SpaView` removed
- `src/config/settings/base.py` — `FRONTEND_DIST`, `SPA_INDEX_FILE`, and the
  `STATICFILES_DIRS` append removed
- `.github/workflows/ci.yml` — `frontend-quality`, `frontend-test`, `frontend-build` removed
  plus their `needs:` entries and the Windows job's frontend step
- `.github/workflows/maintenance.yml` — the npm audit step, summary block, and artifact
- `codecov.yml`, `sonar-project.properties` — Python-only
- `tests/unit/{test_settings_paths,test_dev_runner_config,test_landing_page}.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Deleted the React SPA and every trace of its build chain: the `frontend/` tree, the `nodejs` dependency, the eight `fe-*` pixi tasks and their `ci` entries, the Vite process, the Docker build step, three GitHub CI jobs, the npm audit, and the frontend halves of the Codecov and Sonar configs. Removed the AD-5 coupling — `SpaView`, the catch-all, `SPA_INDEX_FILE`, `FRONTEND_DIST` — with no route left behind: the ten routes were transcribed out of `App.tsx` and asserted to resolve *and* respond before anything was deleted, and re-checked live afterwards. An unknown path now 404s, implementing the decision Story 21.18 flagged. Verified on a clean checkout: `pixi install --locked` yields an environment with no `node` or `npm`, the suite passes in it, and `pixi run dev` brings up web + worker + beat with the UI at `:8000`. `pixi run ci` exit 0; 806 tests at 96.72%. Documentation still describing the SPA is Story 21.21's scope. |
