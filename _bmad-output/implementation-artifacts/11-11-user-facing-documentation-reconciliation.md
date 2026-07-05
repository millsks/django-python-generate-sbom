# Story 11.11: User-Facing Documentation Reconciliation (Org Membership)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Implement AFTER Epic 2 is done. The exact UI wording/screenshots depend on the shipped behavior — verify every claim against the running app before finalizing.

## Story

As an end user,
I want the User Guide and How-To guides to match how accounts and organizations actually work,
so that the instructions I follow don't lead me into errors or dead ends.

## Acceptance Criteria

1. **Accounts & orgs guide reflects zero-org signup.** `docs/user-guide/accounts-and-organizations.md` reflects: a newly registered user has **no** org (not a personal org) and is shown a "create one or ask an admin to add you" state, how to **create an organization** from the UI, switching orgs, and that platform (global) admins oversee all orgs. (FR-DOC2)
2. **Manage-org how-to reflects add-by-email.** `docs/how-to/manage-organization.md` documents adding a member by their **registered email** (and the "no such user" outcome), removing members, the last-admin rule, and create/switch org — with **no** references to temporary passwords or auto-created accounts. (FR-DOC3)
3. **No stale wording/screenshots; strict build green.** Stale screenshots/wording on these pages are updated; `pixi run docs-build` (`mkdocs build --strict`) passes.

## Tasks / Subtasks

- [ ] **Task 1 — Accounts & Organizations (AC: #1)**
  - [ ] Review `docs/user-guide/accounts-and-organizations.md` against the shipped Epic 2 flow. Replace any "personal org on signup" narrative with: register → zero orgs → create-org affordance / wait to be added; org switcher; global-admin oversight.
- [ ] **Task 2 — Manage organization how-to (AC: #2)**
  - [ ] Review `docs/how-to/manage-organization.md` ("Invite a member / switch organizations"). Rewrite the invite flow to add-existing-user-by-email (Story 2.7), including the not-found error; remove temp-password language; cover remove + last-admin (Story 2.9) and create/switch org (Story 2.5).
- [ ] **Task 3 — Verify + build (AC: #3)**
  - [ ] Update/replace any screenshots that no longer match; run `pixi run docs-build` (strict) and fix any broken links/nav.

## Dev Notes

### What changed in Epic 2 (drivers for this reconciliation)

- **2.5** create-org from the UI. **2.6** zero-org registration + the no-org empty state (no personal org). **2.7** add member by existing email (no temp password / no auto-create) + remove. **2.8** global-admin ADMIN org overseeing all orgs. **2.9** membership edge cases (last-admin protection).
- Cross-check the shipped strings/labels (empty-state copy, error messages like "No registered user with that email") against the final UI so the docs quote them accurately.

### Scope / coordination

- User-facing pages only (User Guide + How-To). API contract details go in **11.12**; developer/architecture details in **11.13**; README + general sweep in **11.14** — avoid overlap.

### Project Structure Notes

- Docs under `docs/user-guide/` and `docs/how-to/`; nav in `mkdocs.yml`. Build gate: `pixi run docs-build` (`mkdocs build --strict`), part of `pixi run ci`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 11.11]
- Epic 2 stories: `_bmad-output/implementation-artifacts/2-5..2-9-*.md`
- Docs: `docs/user-guide/accounts-and-organizations.md`, `docs/how-to/manage-organization.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
