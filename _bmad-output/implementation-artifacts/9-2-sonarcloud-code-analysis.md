# Story 9.2: SonarCloud Code Analysis

Status: review

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

claude-opus-4-8[1m]

### Completion Notes List

- Added a `sonar` job to `.github/workflows/ci.yml` (`needs: [backend-test, frontend-test]`) that regenerates both coverage reports in-job via the Story 9.1 pixi tasks (`cov-xml`, `fe-cov`) and scans with `SonarSource/sonarqube-scan-action@v5`. Coverage is regenerated rather than passed as artifacts (simpler; mirrors idp-app's approach).
- Graceful no-op: a "Check for SONAR_TOKEN" step (reads the secret via env, not shell interpolation) gates the coverage + scan steps on `present == 'true'`, so runs without the secret succeed with a notice instead of failing. The job is also skipped for pull requests from forks (which cannot access the secret).
- `sonar-project.properties` is based on idp-app's file, adapted to this repo: `projectKey=millsks_django-python-generate-sbom`, `sources=backend/generate_sbom,frontend/src`, Django `**/migrations/**` exclusion (replacing idp-app's alembic), coverage paths `backend/coverage.xml` + `frontend/coverage/lcov.info`, and `sonar.host.url=https://sonarcloud.io` (required by the scan action for the cloud service).
- Did not modify `pixi.toml` (reuses existing tasks); adding the job/config does not change `pixi run ci`, which remains green.
- Operator prerequisites: create a SonarCloud project bound to this repo and add a `SONAR_TOKEN` repository secret; confirm the exact projectKey/organization match the SonarCloud project. Until the token is set, the sonar job no-ops.

### File List

- `.github/workflows/ci.yml` (added `sonar` job)
- `sonar-project.properties` (new)
- `_bmad-output/implementation-artifacts/9-2-sonarcloud-code-analysis.md` (this file)
