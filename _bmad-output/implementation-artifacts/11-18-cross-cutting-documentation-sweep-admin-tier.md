# Story 11.18: Cross-Cutting Documentation Sweep (2nd Pass)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Run LAST in the Epic 11 second reopen, after 11.15–11.17 and against the **then-current merged state** (at minimum through **Story 13.1**; recommended after Stories 2.18–2.20 merge). This sweep catches whatever the audience-scoped stories didn't.

## Story

As a maintainer,
I want a final sweep of the README and full docs tree for drift since the last pass,
so that the published docs and README are trustworthy after the admin-tier, landing-page, and nav changes.

## Acceptance Criteria

1. **README front page accurate.** The root `README.md` reflects the current app: role model (member / org-admin / global-admin), zero-org registration, create-org gating, the landing page (Story 12.8), and current nav (login→index, home nav item, account-menu shows the user, dashboard removed — Epic 10). Any stale personal-org / transfer-admin / registration wording is corrected. (FR-DOC7)
2. **Full-tree drift audited.** The whole `docs/` tree is audited for dated screenshots, navigation descriptions, and prose from recent work (the landing page 12.8, nav changes in Epic 10, admin screens, and the version-currency 8.22–8.24 changes); stale items are refreshed and the auto-generated code reference (mkdocstrings) still renders.
3. **Link integrity + closure.** `pixi run docs-build` (`mkdocs build --strict`) passes with no broken links/nav; anything found but out of scope for 11.15–11.17 is fixed here or explicitly noted.

## Tasks / Subtasks

- [ ] **Task 1 — README (AC: #1)**
  - [ ] Audit root `README.md`: correct any personal-org / transfer-admin / registration wording; reflect the role model, zero-org registration, create-org gating, the landing page, and current nav; verify links to the docs site.
- [ ] **Task 2 — Full docs sweep (AC: #2)**
  - [ ] Walk every page under `docs/` (user-guide, how-to, developer, api, index, contributing). Flag/refresh dated screenshots and prose from the landing page (12.8), nav changes (Epic 10: login→index, home nav, account-menu user, dashboard removed), admin screens, and version-currency changes (8.22–8.24). Confirm mkdocstrings code reference renders.
- [ ] **Task 3 — Strict build + closure (AC: #3)**
  - [ ] Run `pixi run docs-build` (strict); fix broken links/nav. Record anything intentionally deferred.

## Dev Notes

### Why a second sweep (beyond 11.15–11.17)

- 11.15 (user-facing), 11.16 (API), 11.17 (developer) are scoped to the admin-tier / authorization / version-currency changes. This story catches everything else: the README front page, screenshots dated by Story 12.8's landing page and Epic 10's nav changes (login→index, home nav item, account-menu user, dashboard removed), and any link/nav breakage. `mkdocs build --strict` (wired into `pixi run ci` via `docs-build`) is the backstop for link integrity.
- Screenshots are the most likely stale asset after the landing-page and nav work — check every embedded image against the current UI.

### Scope / coordination

- Deliberately last. Don't re-edit what 11.15–11.17 own; fix gaps and cross-cutting assets (README, images, links). If a large drift area surfaces that deserves its own story, note it rather than expanding scope here.
- Second pass: **11.14** swept after the initial org-membership work; this pass sweeps after the admin tier, landing page, nav changes, and version-currency updates.

### Project Structure Notes

- Root `README.md` + entire `docs/` tree; images likely under `docs/` asset folders. Build gate: `pixi run docs-build`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 11.18]
- Related: Story 11.7 (README overhaul), Story 12.8 (landing page), Epic 10 (navigation), Stories 8.22–8.24 (version currency)
- Prior pass: `11-14-cross-cutting-documentation-audit-and-refresh.md`

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Opus 4.8, 1M context)

### Debug Log References

- `pixi run docs-build` (`mkdocs build --strict`) — green, no broken links/nav.
- `pixi run ci` — green.

### Completion Notes List

- Run last, after 11.15–11.17. Swept the whole `docs/` tree plus the root `README.md`.
- `README.md`: corrected the quick-start onboarding — a new user is **restricted to home until an admin adds them**, and **create-org is reserved for global admins** (the seeded superuser, as a global admin, creates the first org); added the three-tier role summary (member / org-admin / global-admin). Nav description (login→index, home nav, account-menu user, dashboard removed) verified accurate; landing-page/features copy already current.
- Full-tree audit: fixed the stale "history dashboard" screenshot caption in `user-guide/job-history.md`. Confirmed no other "dashboard / transfer-admin / personal-org / hand-over" drift remains (remaining matches are correct in-context, e.g. "does not create a personal org"). The mkdocstrings code reference renders.
- Screenshots across the tree are placeholder notes only (no images are committed), so there were no dated image assets to refresh; left the placeholders in place per the story's guidance.
- No large out-of-scope drift area surfaced that warrants its own story.

### File List

- `README.md`
- `docs/user-guide/job-history.md`
</content>
