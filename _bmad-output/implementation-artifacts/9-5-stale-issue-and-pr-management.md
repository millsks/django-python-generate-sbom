# Story 9.5: Stale Issue & PR Management

Status: review

<!-- Ports idp-app/.github/workflows/stale.yml. -->

## Story

As a maintainer,
I want stale issues/PRs handled automatically,
so that the backlog stays current.

## Acceptance Criteria

1. Given the stale workflow (mirroring `idp-app/.github/workflows/stale.yml`), when it runs on `schedule` / `workflow_dispatch`, then `actions/stale@v9` marks and eventually closes stale issues and PRs per configured `days-before-stale` / `days-before-close`, stale labels, and exempt labels (FR-CI5).
2. Given exemptions, when configured, then pinned/security/in-progress labels (and assignees/milestones as appropriate) are exempt from staling.
3. Given messages, when an item goes stale, then a clear comment explains the policy and how to keep it open.

## Tasks / Subtasks

- [x] Task 1 — Stale workflow (AC: #1, #2, #3)
  - [x] Add `.github/workflows/stale.yml` with `schedule` + `workflow_dispatch` and `actions/stale@v9`
  - [x] Configure days/labels/messages/exemptions to match the idp-app policy (adapted)
- [x] Task 2 — Verify workflow validity + label existence for stale labels

## Dev Notes

Source: `idp-app/.github/workflows/stale.yml` (`actions/stale@v9`, scheduled). Straightforward port; align the day thresholds and exempt labels with this project's conventions. Ensure the stale labels exist (coordinate with Story 9.6's label bootstrap).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Ported `idp-app/.github/workflows/stale.yml` to `.github/workflows/stale.yml` using `actions/stale@v9` on `schedule` (daily 1 AM UTC) + `workflow_dispatch` (AC #1).
- Kept idp-app's day thresholds (issues 60→7, PRs 30→14) and `operations-per-run: 100`.
- Exemptions (AC #2): added `in-progress` alongside `pinned`/`security` to both `exempt-issue-labels` and `exempt-pr-labels`; retained idp-app's bug/enhancement/good-first-issue (issues) and dependencies/automated (PRs); added `exempt-all-milestones: true` so milestoned items are exempt.
- Stale/close messages (AC #3) explain the policy and how to keep an item open (comment / rebase / add an exempt label).
- `stale` labels are bootstrapped by Story 9.6's label automation; this workflow references them by name.
- `pixi run ci` green locally (this change is a GitHub Actions workflow YAML only; no code/test/coverage surface touched).

### File List

- `.github/workflows/stale.yml` (new)
