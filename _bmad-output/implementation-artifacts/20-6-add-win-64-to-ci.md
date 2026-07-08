# Story 20.6: Add win-64 to CI

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 20.5** (the cross-platform tasks the Windows job exercises must exist and
> pass locally first). Depends on Story 20.2's `win-64` environment.

## Story

As a maintainer,
I want a Windows job in the CI matrix running the unit suite,
so that cross-platform regressions (POSIX paths, Celery pool, gunicorn) are caught automatically, not by a
developer on Windows.

## Acceptance Criteria

1. **A Windows CI job exists.**
   Given `.github/workflows/ci.yml` runs every job on `runs-on: ubuntu-latest` with **no OS matrix** (verified),
   when this story lands, then a job runs on `windows-latest` using `prefix-dev/setup-pixi@v0.8.1` against the
   `win-64` environment (Story 20.2) and executes the backend + frontend **unit** suites (`pixi run test` /
   the frontend test task) — giving Windows coverage the pipeline has zero of today.
2. **Windows-relevant paths are exercised.**
   Given the Windows-specific risks are POSIX paths (`/tmp` beat schedule), the Celery pool (prefork is
   Unix-only), and gunicorn (Unix-only), when the Windows job runs the unit suite under
   `config.settings.local` (SQLite + filesystem + eager Celery), then the tests pass on `windows-latest` —
   confirming the portable paths (Story 20.4) and settings (Story 20.3) hold on Windows without needing a
   broker/worker/gunicorn in CI.
3. **No gunicorn dependency on the Windows job.**
   Given gunicorn is scoped off `win-64` (Story 20.2), when the Windows job installs the environment, then it
   resolves without gunicorn and the unit suite does not import or require it (the eager test path needs no
   web server or real worker).
4. **Existing Ubuntu jobs unchanged; matrix documented.**
   Given the current Ubuntu-only jobs (`backend-quality`, `backend-test`, `frontend-*`, `*-build`, `sonar`),
   when the Windows job is added, then the existing jobs are unchanged (Windows is **additive**), the Windows
   job is `continue-on-error`-scoped only if agreed (default: a required check), and the header note in
   `ci.yml` (currently explaining the single-locked-env rationale, L17–21) is updated to record that a
   `win-64` cross-platform job now runs the unit suite.

## Tasks / Subtasks

- [ ] **Task 1 — Windows unit job (AC: #1, #3)** — Add a `unit-windows` (or matrix `os: [ubuntu-latest,
  windows-latest]`) job to `.github/workflows/ci.yml` using `setup-pixi@v0.8.1` and running the backend +
  frontend unit tests on `windows-latest`; confirm the install resolves the `win-64` env without gunicorn.
- [ ] **Task 2 — Path/settings coverage (AC: #2)** — Ensure the Windows job runs under
  `config.settings.local` (eager Celery, SQLite, portable paths) so the POSIX-path and pool risks are actually
  exercised; keep it to the fast unit suite (no broker/worker).
- [ ] **Task 3 — Keep Ubuntu jobs + doc note (AC: #4)** — Leave the existing Ubuntu jobs untouched; update the
  `ci.yml` header comment to mention the win-64 cross-platform job.

## Dev Notes

### Grounded facts (verified)

- `.github/workflows/ci.yml`: **no OS matrix, no python-version matrix** — every job is `runs-on:
  ubuntu-latest`; jobs are `backend-quality` (L25–41), `backend-test` (L44–63), `frontend-quality` (L66–78),
  `frontend-test` (L81–100), `backend-build` (L103–114), `frontend-build` (L117–128), `docker-build`
  (L131–146), `sonar` (L152–188). Each uses `prefix-dev/setup-pixi@v0.8.1`. The header comment (L17–21)
  explains why there is no python matrix (single pixi-locked interpreter). **No `windows`/`win-64` anywhere.**
- The `win-64` pixi environment (Story 20.2) and the eager test path + portable paths (Stories 20.3/20.4) are
  the preconditions this job validates.

### Scope — unit suite only

The Windows job runs the **unit** suite (offline, eager Celery, SQLite). It deliberately does **not** run a
real broker/worker or gunicorn on Windows — those cross-platform paths are covered by the local `pixi run dev`
verification (Story 20.5). CI's job is to catch path/pool/import regressions cheaply.

### Testing standards

- The deliverable is the CI job itself; "green on `windows-latest`" is the acceptance signal. No new
  application tests are required beyond confirming the existing unit suite passes on Windows.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.6: Add win-64 to CI]
- `.github/workflows/ci.yml` (L17–21 header note; existing jobs L25–188), `pixi.toml` (`win-64` platform).
- Upstream: `20-2-add-win-64-platform-and-verify-env.md`, `20-3-containerless-local-dev-settings.md`,
  `20-4-cross-platform-async-worker.md`, `20-5-cross-platform-pixi-tasks-and-dev-runner.md`.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

- Validated on a real `windows-latest` GitHub Actions runner via `gh pr checks --watch` on the story PR.

### Completion Notes List

- Added an additive `unit-windows` job to `.github/workflows/ci.yml` running on
  `windows-latest` via `prefix-dev/setup-pixi@v0.8.1`, executing the backend unit
  suite (`pixi run test`) and the frontend unit suite (`pixi run fe-test`) against
  the gunicorn-free `win-64` pixi environment (AC #1, #3).
- Backend unit suite runs under `config.settings.test` (inherits `config.settings.local`:
  eager Celery, SQLite, portable `.celery/` beat path), so the POSIX-path / Celery-pool /
  gunicorn-import risks are exercised offline with no broker, worker, or web server (AC #2).
- Existing Ubuntu jobs left untouched; the Windows job is a required check (not
  `continue-on-error`) per AC #4 default. Updated the `ci.yml` header note to record the
  new win-64 cross-platform unit job (AC #4).
- Local `pixi run ci` remains green; the Windows job runs only on GitHub Actions.

### File List

- `.github/workflows/ci.yml` (modified — header note + `unit-windows` job)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — 20.5 done, 20.6 review)
- `_bmad-output/implementation-artifacts/20-6-add-win-64-to-ci.md` (modified — status + Dev Agent Record)
