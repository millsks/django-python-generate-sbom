# Story 9.3: Automated Release Workflow

Status: review

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

claude-opus-4-8[1m]

### Completion Notes List

- Added `.github/workflows/release.yml`, porting idp-app's release workflow to this repo's pixi umbrella toolchain.
- Triggers: `schedule` (00:00 UTC on the 7th & 21st) + `workflow_dispatch` (inputs: `version`, `prerelease`, `force_recreate`); a `concurrency` group serializes releases.
- Auth via `actions/create-github-app-token@v1` (secrets `APP_ID` + `APP_PRIVATE_KEY`) so the tag/changelog commit pushes past branch protection; documented as an operator prerequisite in a header comment.
- Version derivation mirrors the source: read the latest `v*` tag, auto-increment the patch (first release → `0.1.0`), or accept an explicit `version` input; semver-validated; `force_recreate` deletes an existing tag/release first.
- Graceful no-op: when `git diff` shows no changes since the last tag, every downstream step is gated off (`should_skip`), so no empty tag/release is cut.
- Quality gate is the authoritative `pixi run ci`; changelog generated with `pixi run changelog` (git-cliff + existing `cliff.toml`); the release is published with `softprops/action-gh-release@v2`.
- Adapted artifacts to this repo: a backend wheel (`backend/dist/*.whl` via `pixi run build`) and a frontend bundle tarball (`pixi run fe-build` → archived) — no conda package or PyPI publishing (idp-app-only).
- `pixi run ci` green locally (no code paths changed); `release.yml` parses as valid YAML.

### File List

- `.github/workflows/release.yml` (new)
