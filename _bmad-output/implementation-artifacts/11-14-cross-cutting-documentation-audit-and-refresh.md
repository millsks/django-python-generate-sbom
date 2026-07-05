# Story 11.14: Cross-Cutting Documentation Audit & Refresh

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Run LAST in the Epic 11 reopen, after 11.11-11.13 and after Epic 2 is done — this sweep catches whatever those audience-scoped stories didn't.

## Story

As a maintainer,
I want a final sweep of all documentation for drift beyond the org-membership changes,
so that the published docs and README are trustworthy after the recent epics.

## Acceptance Criteria

1. **README front page accurate.** Any personal-org / registration wording in the root `README.md` is corrected, and the overview, quick start, and screenshots reflect the current app. (FR-DOC7)
2. **Full-tree drift audited.** The whole `docs/` tree is audited for dated screenshots, navigation descriptions, and prose from recent UI work (Epic 12 visual polish, Epic 10 navigation); stale items are refreshed and the auto-generated code reference (mkdocstrings) still renders.
3. **Link integrity + closure.** `pixi run docs-build` (`mkdocs build --strict`) passes with no broken links/nav; anything found but out of scope for 11.11-11.13 is fixed here or explicitly noted.

## Tasks / Subtasks

- [ ] **Task 1 — README (AC: #1)**
  - [ ] Audit root `README.md` for personal-org/registration wording and stale quick-start/screenshots; correct to the shipped behavior; verify links to the docs site.
- [ ] **Task 2 — Full docs sweep (AC: #2)**
  - [ ] Walk every page under `docs/` (user-guide, how-to, developer, api, index, contributing). Flag/refresh dated screenshots and prose from Epic 12 (visual design) and Epic 10 (navigation shell). Confirm mkdocstrings code reference renders.
- [ ] **Task 3 — Strict build + closure (AC: #3)**
  - [ ] Run `pixi run docs-build` (strict); fix broken links/nav. Record anything intentionally deferred.

## Dev Notes

### Why a sweep (beyond 11.11-11.13)

- 11.11 (user-facing), 11.12 (API), 11.13 (developer) are scoped to the org-membership changes. This story catches everything else: the README front page, screenshots dated by Epic 12's visual redesign and Epic 10's nav shell, and any link/nav breakage. `mkdocs build --strict` (already wired into `pixi run ci` via `docs-build`) is the backstop for link integrity.
- Screenshots are the most likely stale asset after the Epic 12 polish — check every embedded image against the current UI.

### Scope / coordination

- Deliberately last. Don't re-edit what 11.11-11.13 own; fix gaps and cross-cutting assets (README, images, links). If a large drift area surfaces that deserves its own story, note it rather than expanding scope here.

### Project Structure Notes

- Root `README.md` + entire `docs/` tree; images likely under `docs/` asset folders. Build gate: `pixi run docs-build`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 11.14]
- Related: Story 11.7 (README overhaul), Epic 12 (visual polish), Epic 10 (navigation)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
