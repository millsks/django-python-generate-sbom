# Story 9.4: Repository Maintenance Workflow

Status: ready-for-dev

<!-- Ports idp-app/.github/workflows/maintenance.yml. -->

## Story

As a maintainer,
I want scheduled repository maintenance,
so that old workflow runs are pruned and dependencies are audited.

## Acceptance Criteria

1. Given the maintenance workflow (mirroring `idp-app/.github/workflows/maintenance.yml`), when it runs on `schedule` / `workflow_dispatch`, then a **cleanup-artifacts** job prunes old workflow runs (e.g. `Mattraks/delete-workflow-runs`) per a retention policy (FR-CI4).
2. Given the same workflow, when it runs, then a **security-audit** job runs a dependency/security audit via pixi and uploads the report as an artifact (`actions/upload-artifact`).
3. Given the audit, when it finds issues, then it surfaces them (job annotation/summary) without necessarily failing the scheduled run (documented policy).

## Tasks / Subtasks

- [ ] Task 1 — Maintenance workflow (AC: #1, #2)
  - [ ] Add `.github/workflows/maintenance.yml` with `schedule` + `workflow_dispatch`
  - [ ] `cleanup-artifacts` job: `Mattraks/delete-workflow-runs` with retention inputs
  - [ ] `security-audit` job: `setup-pixi`, run the audit task, `upload-artifact` the report
- [ ] Task 2 — Audit task
  - [ ] Ensure a `pixi run` audit task exists (e.g. pip-audit for Python deps; `npm audit` for frontend); wire it in
- [ ] Task 3 — Verify workflow validity + retention values

## Dev Notes

Source: `idp-app/.github/workflows/maintenance.yml` (jobs: `cleanup-artifacts` via `Mattraks/delete-workflow-runs`; `security-audit` via `setup-pixi` + `upload-artifact`). Adapt the audit to this repo's toolchain (pip-audit / npm audit through pixi tasks). Keep the scheduled cadence and retention policy configurable.

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
