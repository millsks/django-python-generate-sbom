# Story 9.1: Comprehensive CI Workflow

Status: ready-for-dev

<!-- Ports idp-app/.github/workflows/ci.yml, adapted to this repo's pixi/ruff/mypy/oxlint/vitest toolchain. -->

## Story

As a maintainer,
I want a full CI pipeline mirroring idp-app's,
so that every push/PR is quality-checked, tested with coverage, and built.

## Acceptance Criteria

1. Given a push or PR, when CI runs, then it executes these jobs (adapted from `idp-app/.github/workflows/ci.yml`): a `concurrency` group; **backend-quality** (ruff lint, ruff format check, mypy, bandit security scan); **backend-test** (`needs: backend-quality`) uploading coverage to Codecov; **frontend-quality** (oxlint, `tsc` type check); **frontend-test** (`needs: frontend-quality`) uploading coverage to Codecov; **backend-build**; **frontend-build**; **docker-build** validating the image(s) build (FR-CI1).
2. Given the pixi umbrella toolchain, when each job sets up, then it uses `prefix-dev/setup-pixi` and runs `pixi run` tasks (no bespoke Python/Node setup).
3. Given the existing scaffold `ci.yml`, when this lands, then it is expanded/replaced by the comprehensive workflow while `pixi run ci` stays the local gate; keep the multi-Python-version matrix intent where sensible.
4. Given Codecov, when configured, then it uses `codecov/codecov-action@v5`; the story documents the Codecov setup (token needed if private).
5. Given bandit isn't a current dependency, when the security scan is added, then bandit is added to the dev toolchain (a new dev dependency — flag it) with a `pixi run` task.

## Tasks / Subtasks

- [ ] Task 1 — Adapt the CI workflow (AC: #1, #2, #3)
  - [ ] Rewrite `.github/workflows/ci.yml` with the job graph above; `concurrency` to cancel superseded runs; `setup-pixi` per job; `pixi run <task>` steps
  - [ ] Map jobs to existing/added pixi tasks: `lint` (ruff), `fmt`-check, `check` (mypy), `test`/`cov`, `fe-lint`, `fe-test`, `build`, `fe-build`
- [ ] Task 2 — Backend security scan (AC: #5)
  - [ ] Add bandit to `[feature.dev]`/lint deps; add a `pixi run security` (bandit -r backend/generate_sbom) task; wire into backend-quality
- [ ] Task 3 — Coverage uploads (AC: #4)
  - [ ] Emit coverage XML for backend (pytest-cov) and frontend (vitest coverage); `codecov/codecov-action@v5` in the test jobs
- [ ] Task 4 — docker-build (AC: #1)
  - [ ] A job that builds the Docker image(s) (buildx) to validate they build (no push)
- [ ] Task 5 — Verify
  - [ ] `pixi run ci` still green locally; the workflow is valid (actionlint or a dry review); document Codecov prerequisite

## Dev Notes

Source: `idp-app/.github/workflows/ci.yml` (jobs: backend-quality, backend-test+Codecov, frontend-quality, frontend-test+Codecov, backend-build, frontend-build, sonar, docker-build). **Sonar is split into Story 9.2.** Adapt tools to THIS repo: frontend uses **oxlint** (not ESLint) and has no Prettier; backend uses ruff/mypy/pytest via pixi. The local harness (`pixi run ci`) is authoritative and must stay green; CI mirrors it plus Codecov + docker-build.

Prerequisite (operator): Codecov app/integration; a `CODECOV_TOKEN` secret if the repo is private.

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
