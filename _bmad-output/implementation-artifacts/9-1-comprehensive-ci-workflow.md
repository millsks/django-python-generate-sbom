# Story 9.1: Comprehensive CI Workflow

Status: review

<!-- Ports idp-app/.github/workflows/ci.yml, adapted to this repo's pixi/ruff/mypy/oxlint/vitest toolchain. -->

## Story

As a maintainer,
I want a full CI pipeline mirroring idp-app's,
so that every push/PR is quality-checked, tested with coverage, and built.

## Acceptance Criteria

1. Given a push or PR, when CI runs, then it executes these jobs (adapted from `idp-app/.github/workflows/ci.yml`): a `concurrency` group; **backend-quality** (ruff lint, ruff format check, mypy, bandit security scan); **backend-test** (`needs: backend-quality`) uploading coverage to Codecov; **frontend-quality** (oxlint, `tsc` type check); **frontend-test** (`needs: frontend-quality`) uploading coverage to Codecov; **backend-build**; **frontend-build**; **docker-build** validating the image(s) build (FR-CI1).
2. Given the pixi umbrella toolchain, when each job sets up, then it uses `prefix-dev/setup-pixi` and runs `pixi run` tasks (no bespoke Python/Node setup).
3. Given the existing scaffold `ci.yml`, when this lands, then it is expanded/replaced by the comprehensive workflow while `pixi run ci` stays the local gate; keep the multi-Python-version matrix intent where sensible.
4. Given Codecov needs data for **both** components, when CI runs, then **backend** coverage AND **frontend** coverage are each uploaded to Codecov via `codecov/codecov-action@v5`, each tagged with a distinct **flag** (`backend` / `frontend`) so Codecov tracks them separately (not one merged number).
5. Given backend coverage upload, when the backend-test job runs, then it produces a machine-readable report (`coverage.xml` via `pytest --cov --cov-branch --cov-report=xml`, per Codecov's setup) that the Codecov action consumes.
6. Given frontend coverage upload, when the frontend-test job runs, then vitest produces coverage in a Codecov-consumable format (v8 provider, `lcov` reporter) — this requires **adding a coverage script/pixi task and vitest coverage config** (the frontend has `@vitest/coverage-v8` but no coverage script/config today).
7. Given multi-component reporting, when configured, then a `codecov.yml` defines the `backend` and `frontend` flags/components (paths + targets) so each shows independently in Codecov.
8. Given bandit isn't a current dependency, when the security scan is added, then bandit is added to the dev toolchain (a new dev dependency — flag it) with a `pixi run` task.

## Tasks / Subtasks

- [ ] Task 1 — Adapt the CI workflow (AC: #1, #2, #3)
  - [ ] Rewrite `.github/workflows/ci.yml` with the job graph above; `concurrency` to cancel superseded runs; `setup-pixi` per job; `pixi run <task>` steps
  - [ ] Map jobs to existing/added pixi tasks: `lint` (ruff), `fmt`-check, `check` (mypy), `test`/`cov`, `fe-lint`, `fe-test`, `build`, `fe-build`
- [ ] Task 2 — Backend security scan (AC: #5)
  - [ ] Add bandit to `[feature.dev]`/lint deps; add a `pixi run security` (bandit -r backend/generate_sbom) task; wire into backend-quality
- [ ] Task 3 — Coverage generation for both components (AC: #4, #5, #6, #7)
  - [ ] **Backend:** add a `--cov-report=xml` output (a CI cov command or extend the `cov` task) so `coverage.xml` is produced
  - [ ] **Frontend:** add a `test:coverage` npm script + `fe-cov` pixi task (`vitest run --coverage`) and vitest coverage config (provider `v8`, reporters `text` + `lcov`); ensure `@vitest/coverage-v8` is wired
  - [ ] Upload BOTH in the respective test jobs with `codecov/codecov-action@v5`, `flags: backend` and `flags: frontend` (+ the file path each)
  - [ ] Add `codecov.yml` defining the `backend` and `frontend` flags/components (with `paths`) so each is tracked independently
- [ ] Task 4 — docker-build (AC: #1)
  - [ ] A job that builds the Docker image(s) (buildx) to validate they build (no push)
- [ ] Task 5 — Verify
  - [ ] `pixi run ci` still green locally; the workflow is valid (actionlint or a dry review); document Codecov prerequisite

## Dev Notes

Source: `idp-app/.github/workflows/ci.yml` (jobs: backend-quality, backend-test+Codecov, frontend-quality, frontend-test+Codecov, backend-build, frontend-build, sonar, docker-build). **Sonar is split into Story 9.2.** Adapt tools to THIS repo: frontend uses **oxlint** (not ESLint) and has no Prettier; backend uses ruff/mypy/pytest via pixi. The local harness (`pixi run ci`) is authoritative and must stay green; CI mirrors it plus Codecov + docker-build.

Prerequisite (operator): Codecov app/integration; a `CODECOV_TOKEN` secret if the repo is private.

### Codecov coverage commands (from Codecov's setup UI)

Per Codecov's own per-language instructions for this repo:

- **Backend (Pytest):** `pytest --cov --cov-branch --cov-report=xml` → produces `coverage.xml`. (Adds `--cov-branch` for branch coverage on top of the existing `--cov=generate_sbom`.)
- **Frontend (Vitest):** `npx vitest run --coverage` (deps `vitest @vitest/coverage-v8` — already present). Configure vitest coverage to emit `lcov` so Codecov can consume it.

Upload each with `codecov/codecov-action@v5` under a distinct `flags:` (`backend` / `frontend`) and its report path, so Codecov reports both components separately (AC #4). Define the two flags/components in `codecov.yml`.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Replaced the scaffold `ci.yml` with 7 jobs: **backend-quality** (lint, fmt-check,
  mypy, bandit), **backend-test** (`needs: backend-quality`) → Codecov `backend` flag,
  **frontend-quality** (oxlint, tsc), **frontend-test** (`needs: frontend-quality`) →
  Codecov `frontend` flag, **backend-build**, **frontend-build** (each `needs` its
  quality job), and **docker-build** (`needs` both quality jobs; buildx build, no push,
  gha cache). `concurrency` cancels superseded runs; every job uses
  `prefix-dev/setup-pixi@v0.8.1` + `pixi run`.
- Backend coverage: new `cov-xml` pixi task = `pytest --cov=generate_sbom --cov-branch
  --cov-report=xml` (+ term-missing + `--cov-fail-under=90`), producing
  `backend/coverage.xml`. The existing `cov` task (local gate) is unchanged.
- Frontend coverage: added `test:coverage` script (`vitest run --coverage`) + `fe-cov`
  pixi task, and vitest coverage config (provider `v8`, reporters `text`+`lcov`) →
  `frontend/coverage/lcov.info`. `@vitest/coverage-v8` was already a dev dep.
- Both coverages upload via `codecov/codecov-action@v5` with distinct `flags`
  (`backend` / `frontend`) and `fail_ci_if_error: false` (so CI is green before the
  operator wires Codecov). `codecov.yml` defines both flags + named components with
  path scoping so each is tracked independently.
- Wired `fmt-check`, `security`, and `fe-typecheck` into the local `ci` umbrella (the
  gates Story 9.7 left for 9.1) so `pixi run ci` mirrors the CI quality jobs.
- `coverage.xml` was already gitignored; added `coverage` to `frontend/.gitignore`.
- **Decision — no Python matrix:** the pixi umbrella pins python 3.13 in
  pixi.toml/pixi.lock, so a per-version matrix is cosmetic (setup-pixi runs the locked
  env regardless). Dropped the scaffold's fake matrix and documented that a true
  multi-version matrix needs separate pixi environments (deferred).
- **Operator prerequisites:** enable the Codecov integration for the repo; if the repo
  is private, add a `CODECOV_TOKEN` secret. `docker-build` uses GitHub Actions cache
  (no registry/secret needed).
- `pixi run ci` exits 0 (all 12 tasks); `ci.yml` + `codecov.yml` validated as YAML.

### File List

- `.github/workflows/ci.yml` (rewritten)
- `codecov.yml` (new)
- `pixi.toml` (added `cov-xml`, `fe-cov`; wired `fmt-check`/`security`/`fe-typecheck` into `ci`)
- `frontend/package.json` (added `test:coverage` script)
- `frontend/vitest.config.ts` (v8 coverage config)
- `frontend/.gitignore` (ignore `coverage`)
