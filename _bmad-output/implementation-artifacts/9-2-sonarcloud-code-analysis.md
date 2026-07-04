# Story 9.2: SonarCloud Code Analysis

Status: ready-for-dev

<!-- Ports the `sonar` job from idp-app/.github/workflows/ci.yml. -->

## Story

As a maintainer,
I want SonarCloud static analysis on CI,
so that code quality/security issues are tracked over time.

## Acceptance Criteria

1. Given CI, when the `sonar` job runs, then it invokes the SonarSource scan action, publishing results to SonarCloud (FR-CI2).
2. Given the scan, when it runs, then a `sonar-project.properties` (or action inputs) defines the project key, organization, sources (`backend/`, `frontend/src`), test/exclusion globs, and the coverage report paths (backend coverage.xml, frontend lcov) so coverage shows in Sonar.
3. Given the sonar job depends on coverage, when wired, then it runs after the test jobs (or regenerates coverage) so the reports exist.
4. Given external setup, when implemented, then the story documents the prerequisites: a SonarCloud project bound to the repo and a `SONAR_TOKEN` repository secret. The workflow/config is created here; the operator provisions the token.

## Tasks / Subtasks

- [ ] Task 1 — Sonar config (AC: #2)
  - [ ] Add `sonar-project.properties` with projectKey/org, `sonar.sources`, `sonar.tests`, exclusions, and `sonar.python.coverage.reportPaths` / `sonar.javascript.lcov.reportPaths`
- [ ] Task 2 — Sonar CI job (AC: #1, #3)
  - [ ] Add a `sonar` job using the SonarSource scan action; ensure coverage artifacts are present (needs test jobs or produce coverage in-job)
  - [ ] Pass `SONAR_TOKEN` from secrets
- [ ] Task 3 — Docs (AC: #4)
  - [ ] Document the SonarCloud project + `SONAR_TOKEN` prerequisite in the workflow/README

## Dev Notes

Source: the `sonar` job in `idp-app/.github/workflows/ci.yml` (`SonarSource/sonarcloud-github-action`). Depends on / complements Story 9.1 (coverage). Split out because it needs external SonarCloud provisioning. If the repo shouldn't use SonarCloud, this story can be dropped without affecting 9.1.

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
