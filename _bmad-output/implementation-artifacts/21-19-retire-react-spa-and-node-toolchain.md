# Story 21.19: Retire the React SPA and the Node Toolchain

Status: ready-for-dev

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

- [ ] **Task 0 — Confirm prerequisites** — Every route from `App.tsx` has a Django owner; Story 21.17's
  reference workbooks are committed. Do not proceed otherwise.
- [ ] **Task 1 — Delete `frontend/` (AC: #1)**.
- [ ] **Task 2 — pixi cleanup (AC: #1)** — `nodejs` dependency and the eight `fe-*` tasks; check the `ci` task's
  `depends-on` array for `fe-*` entries.
- [ ] **Task 3 — Remove the SPA coupling (AC: #2)** — `SpaView`, catch-all, `SPA_INDEX_FILE`, `FRONTEND_DIST`,
  `STATICFILES_DIRS`.
- [ ] **Task 4 — Dockerfile + Procfile (AC: #3)**.
- [ ] **Task 5 — CI + maintenance workflows (AC: #4)**.
- [ ] **Task 6 — Codecov + Sonar (AC: #5)**.
- [ ] **Task 7 — Clean-checkout verification (AC: #6)** — Fresh clone, `pixi install`, `pixi run ci`,
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

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
