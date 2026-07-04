# Story 9.7: Adopt Beneficial Pixi Tasks from idp-app

Status: ready-for-dev

<!-- Sources idp-app/pixi.toml [tasks]; adopt the useful ones adapted to this repo's stack. -->

## Story

As a maintainer,
I want the useful pixi tasks that idp-app defines but we lack,
so that quality, security, Docker, and release ergonomics match across the two apps and the CI workflows (Epic 9) have the tasks they call.

## Context

Comparing `idp-app/pixi.toml` to ours, we already have `fmt`, `lint`, `check` (mypy), `test`, `test-integration`, `cov`, `build`, `migrate`, `run`, `worker-*`, `beat`, `changelog`, `precommit`, `act`, `fe-lint`, `fe-test`, `fe-build`, and the `ci` umbrella. The beneficial tasks we're **missing** (adapted to our ruff/mypy/pytest/oxlint/vitest/Django/Celery/Docker stack):

## Acceptance Criteria

1. Given CI needs non-mutating checks, when added, then a **`fmt-check`** task runs `ruff format --check .` (companion to the mutating `fmt`), and a **`lint-fix`** runs `ruff check --fix .` (FR-CI7).
2. Given security scanning, when added, then a **`security`** task runs bandit over `backend/generate_sbom` and a **`fe-security`** task runs `npm audit` for the frontend. (bandit is a new dev dependency — flag it.)
3. Given frontend type checking, when added, then a standalone **`fe-typecheck`** task runs `tsc` without emitting (so CI's frontend-quality job can call it independently of the build).
4. Given local coverage inspection, when added, then a **`cov-html`** task produces an HTML coverage report.
5. Given Docker ergonomics, when added, then convenience tasks wrap the compose stack: **`docker-build`, `docker-up`, `docker-down`, `docker-down-v`, `docker-logs`, `docker-ps`, `docker-migrate`, `docker-shell`** (adapted to this repo's `web`/worker services and `manage.py migrate`).
6. Given Celery monitoring, when added, then a **`flower`** task starts Celery Flower against `config.celery_app`. (flower is a new dev dependency — flag it.)
7. Given pre-commit management, when added, then **`hooks-update`** (`pre-commit autoupdate`) and a commit-msg hook install exist, complementing the existing `bootstrap`/`precommit` tasks.
8. Given release changelog, when added, then a **`changelog-unreleased`** task prepends unreleased commits (`git cliff --unreleased --prepend CHANGELOG.md`).
9. Given the additions, when done, then `pixi run ci` still passes, the new tasks run successfully, and any new dev dependencies (bandit, flower) are added under the dev feature.

## Tasks / Subtasks

- [ ] Task 1 — Quality tasks (AC: #1, #3, #4): `fmt-check`, `lint-fix`, `fe-typecheck`, `cov-html`
- [ ] Task 2 — Security tasks + deps (AC: #2, #9): add bandit dev dep; `security` (bandit) + `fe-security` (npm audit)
- [ ] Task 3 — Docker convenience tasks (AC: #5)
- [ ] Task 4 — Celery flower (AC: #6, #9): add flower dev dep + `flower` task
- [ ] Task 5 — Hooks + changelog (AC: #7, #8): `hooks-update`, commit-msg hook install, `changelog-unreleased`
- [ ] Task 6 — Verify (AC: #9): run each new task; `pixi run ci` green; consider wiring `security`/`fmt-check`/`fe-typecheck` into the `ci` umbrella (coordinate with Story 9.1)

## Dev Notes

Source: `idp-app/pixi.toml` `[tasks]`. **Skip** what doesn't fit our stack: idp-app's `frontend-format`/`format-check` use **Prettier** — we use **oxlint** (no Prettier), so omit those; idp-app is FastAPI/Alembic — our DB tasks use Django `manage.py migrate` (already have `migrate`), so adapt names. New dev deps (bandit, flower) go under `[feature.dev.dependencies]` — flag them as dependency additions. This story complements **9.1** (CI), which calls `fmt-check`, `security`, and `fe-typecheck`.

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
