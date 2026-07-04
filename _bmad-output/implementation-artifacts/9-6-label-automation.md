# Story 9.6: Label Automation

Status: ready-for-dev

<!-- Ports idp-app/.github/workflows/labeler.yml + .github/labeler.yml + .github/issue-labeler.yml. -->

## Story

As a maintainer,
I want issues and PRs auto-labeled,
so that triage is consistent without manual labeling.

## Acceptance Criteria

1. Given the labeler workflow (mirroring `idp-app/.github/workflows/labeler.yml`), when an issue or PR is opened/edited, then it applies labels by **keyword** (`github/issue-labeler` + `.github/issue-labeler.yml`), by **changed paths** (`actions/labeler@v5` + `.github/labeler.yml`), and by **PR size** (`codelytv/pr-size-labeler`) (FR-CI6).
2. Given this repo's layout, when `.github/labeler.yml` is ported, then it maps: `backend` → `backend/**`, `frontend` → `frontend/**`, `docker` → `docker/**` + `docker-compose*.yml`, `ci` → `.github/**`, `documentation` → `**.md` + `docs/**`, `dependencies` → the lockfiles/manifests.
3. Given `.github/issue-labeler.yml` is ported, then keyword regexes map to `bug`, `enhancement`, `documentation`, `question` (adapted from idp-app).
4. Given the referenced labels, when the workflow runs, then those labels exist in the repo (a one-time label bootstrap is documented/provided).

## Tasks / Subtasks

- [ ] Task 1 — Labeler workflow (AC: #1)
  - [ ] Add `.github/workflows/labeler.yml` (on `issues`, `pull_request`) with the three labeling steps + required permissions
- [ ] Task 2 — Config files (AC: #2, #3)
  - [ ] Add `.github/labeler.yml` (path → label) adapted to this repo
  - [ ] Add `.github/issue-labeler.yml` (keyword regex → label)
- [ ] Task 3 — Label bootstrap (AC: #4)
  - [ ] Document (or script) creating the label set the config references
- [ ] Task 4 — Verify workflow validity + permissions

## Dev Notes

Source: `idp-app/.github/workflows/labeler.yml` (`github/issue-labeler@v3.4`, `actions/labeler@v5`, `codelytv/pr-size-labeler@v1`) plus `.github/labeler.yml` and `.github/issue-labeler.yml`. The path map must reflect THIS repo (`backend/`, `frontend/`, `docker/`, `.github/`, docs). Needs `issues: write` / `pull-requests: write` permissions.

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
