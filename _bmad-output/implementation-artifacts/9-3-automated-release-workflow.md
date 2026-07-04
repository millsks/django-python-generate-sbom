# Story 9.3: Automated Release Workflow

Status: ready-for-dev

<!-- Ports idp-app/.github/workflows/release.yml. -->

## Story

As a maintainer,
I want scheduled and on-demand releases with a generated changelog,
so that versioned GitHub Releases are cut without manual steps.

## Acceptance Criteria

1. Given the release workflow (mirroring `idp-app/.github/workflows/release.yml`), when it runs on its `schedule` or via `workflow_dispatch`, then it generates/updates the changelog with **git-cliff** (using the existing `cliff.toml`), determines the next version, and publishes a **GitHub Release** via `softprops/action-gh-release` (FR-CI3).
2. Given the release must push tags/commits under branch protection, when it authenticates, then it uses a **GitHub App token** (`actions/create-github-app-token`) rather than the default `GITHUB_TOKEN` — documented as needing an App ID + private key secret.
3. Given no releasable changes since the last release, when the scheduled run executes, then it no-ops gracefully (no empty tag/release).
4. Given version derivation, when a release is cut, then the version follows the project's scheme (Conventional Commits → semver via git-cliff) and the tag/changelog/release are consistent.

## Tasks / Subtasks

- [ ] Task 1 — Release workflow (AC: #1, #2, #3, #4)
  - [ ] Add `.github/workflows/release.yml` with `schedule` + `workflow_dispatch`; GitHub App token step; `setup-pixi`
  - [ ] Run `pixi run changelog` (git-cliff → CHANGELOG.md) and compute the next version; guard on "no changes"
  - [ ] Create the tag/commit and the GitHub Release (`softprops/action-gh-release@v2`)
- [ ] Task 2 — Docs
  - [ ] Document the GitHub App prerequisite (App ID + private key secrets) and the release cadence
- [ ] Task 3 — Verify
  - [ ] Dry-run via `workflow_dispatch` semantics reviewed; changelog generation matches `cliff.toml`

## Dev Notes

Source: `idp-app/.github/workflows/release.yml` (schedule + dispatch; `actions/create-github-app-token`, `setup-pixi`, `softprops/action-gh-release`). This repo already has `cliff.toml` + `CHANGELOG.md` and a `pixi run changelog` task, so the changelog half is ready. The 12KB reference workflow is comprehensive — port the essential release path (changelog → version → release) and adapt secret names.

Prerequisite (operator): a GitHub App (or PAT) with contents write, exposed as `APP_ID` + `APP_PRIVATE_KEY` secrets.

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
