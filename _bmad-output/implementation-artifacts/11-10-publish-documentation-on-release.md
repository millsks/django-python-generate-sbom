# Story 11.10: Publish Documentation on Release

Status: review

## Story

As a maintainer,
I want the docs rebuilt and republished when a release is cut,
so that the published documentation always reflects the latest release, not just the last docs edit.

## Acceptance Criteria

1. When a release is successfully cut (Story 9.3 `release.yml`), the documentation site is rebuilt and republished to GitHub Pages as part of that run (FR-DOC10).
2. The release publish reuses Story 11.1's build/deploy mechanism rather than duplicating it — `docs.yml`'s build+deploy is exposed as a reusable `workflow_call` workflow that both `docs.yml` (on-push) and `release.yml` (on-release) invoke.
3. A shared GitHub Pages concurrency group (`group: pages`, `cancel-in-progress: false`) serializes the on-push and on-release deploy paths so they don't collide or cancel each other destructively.
4. A no-op release run (no changes since the last tag) does not republish the docs (the release job's `released` output gates the docs job).
5. No new external secret beyond those from Stories 11.1 (Pages = GitHub Actions) and 9.3 (release App token).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- `.github/workflows/docs.yml`: added `workflow_call:` to the `on:` triggers so the build+deploy jobs are reusable. No change to the existing on-push-to-`main` (docs paths) and `workflow_dispatch` triggers, the `pages: write`/`id-token: write` permissions, or the existing `concurrency: group: pages` (reused as the shared serialization group — AC #3).
- `.github/workflows/release.yml`: the `release` job now exposes a `released` output (`steps.should_skip.outputs.skip != 'true'`), true only when a release is actually cut. Added a `publish-docs` reusable-workflow-call job (`uses: ./.github/workflows/docs.yml`) with `needs: release` and `if: needs.release.outputs.released == 'true'`, so it runs only after a real release (skipped on no-op runs — AC #4) and reuses 11.1's deploy (AC #2). It grants `contents: read` / `pages: write` / `id-token: write` and `secrets: inherit`.
- No new secrets required — Pages deploy uses the default `GITHUB_TOKEN` with `pages: write` (AC #5).
- Verified: both workflow YAMLs parse; `pixi run ci` green (no application code touched).

### File List

- `.github/workflows/docs.yml`
- `.github/workflows/release.yml`
