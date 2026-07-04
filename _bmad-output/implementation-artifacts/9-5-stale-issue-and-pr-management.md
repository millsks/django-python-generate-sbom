# Story 9.5: Stale Issue & PR Management

Status: ready-for-dev

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

- [ ] Task 1 — Stale workflow (AC: #1, #2, #3)
  - [ ] Add `.github/workflows/stale.yml` with `schedule` + `workflow_dispatch` and `actions/stale@v9`
  - [ ] Configure days/labels/messages/exemptions to match the idp-app policy (adapted)
- [ ] Task 2 — Verify workflow validity + label existence for stale labels

## Dev Notes

Source: `idp-app/.github/workflows/stale.yml` (`actions/stale@v9`, scheduled). Straightforward port; align the day thresholds and exempt labels with this project's conventions. Ensure the stale labels exist (coordinate with Story 9.6's label bootstrap).

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
