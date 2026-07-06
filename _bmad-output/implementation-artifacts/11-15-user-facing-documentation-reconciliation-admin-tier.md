# Story 11.15: User-Facing Documentation Reconciliation (Admin Tier, 2nd Pass)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** A lot merged after the first reconciliation pass (11.11–11.14 only covered the *initial* Epic 2 org-membership work). Implement this against the **then-current merged state** — at minimum through **Story 13.1** (global-admin management screen). **Recommended:** run after Stories 2.18–2.20 merge so the org-access refinements (zero-org users restricted to home, org-switcher hidden for a single org, demote-admin) are captured in one pass. Verify every claim against the running app before finalizing.

## Story

As an end user,
I want the User Guide and How-To guides to reflect the current roles, admin actions, and zero-org experience,
so that the instructions I follow match what the app actually does now.

## Acceptance Criteria

1. **Accounts & orgs guide covers all three role tiers + the zero-org experience.** `docs/user-guide/accounts-and-organizations.md` documents the **member / org-admin / global-admin** role model, the zero-org experience for a newly registered user (no org; restricted to the home page until an admin adds them — Story 2.18), org switching (and that the switcher is hidden when a user belongs to a single org — Story 2.19), and that **creating an organization is restricted to global admins** (the ADMIN org is hidden from the switcher). (FR-DOC2)
2. **Manage-org how-to covers the full admin toolkit.** `docs/how-to/manage-organization.md` documents the admin actions as shipped: **add an existing user by registered email** (and the "no such user" outcome), **create a new user account** for a member (`orgs/members/create-user/`, Story 2.10), **promote** a member to admin (not "transfer" — Story 2.16), the **demote** admin→member note (Story 2.20), and **remove** a member — with the last-admin rule. No references to temporary-password auto-create as the only add path, and no "transfer admin" wording.
3. **Global-admin management flow is documented.** A user-facing description of the **global-admin management screen** (Story 13.1) exists: who can see it (global admins only), listing current global admins, granting global admin by email, and revoking (removes from the ADMIN org and demotes to member everywhere), including the last-global-admin guard. Placed in the user guide or how-to as appropriate.
4. **No stale wording/screenshots; strict build green.** Stale screenshots/wording on these pages are updated (landing page, nav, admin screens); `pixi run docs-build` (`mkdocs build --strict`) passes.

## Tasks / Subtasks

- [ ] **Task 1 — Accounts & Organizations (AC: #1)**
  - [ ] Update `docs/user-guide/accounts-and-organizations.md`: the three role tiers (member / org-admin / global-admin), the zero-org experience (no org on registration → restricted to home until added — Story 2.18), org switching + single-org switcher hiding (Story 2.19), and create-org restricted to global admins with the ADMIN org hidden from the switcher (Story 2.12).
- [ ] **Task 2 — Manage organization how-to (AC: #2)**
  - [ ] Update `docs/how-to/manage-organization.md`: add-existing-by-email (+ "no such user"), create-new-user (Story 2.10), promote (Story 2.16), demote (Story 2.20), remove + last-admin rule (Story 2.9). Remove any "transfer admin" language.
- [ ] **Task 3 — Global-admin management flow (AC: #3)**
  - [ ] Document the global-admin management screen (Story 13.1): list / grant-by-email / revoke semantics + last-global-admin guard; global-admin-only visibility.
- [ ] **Task 4 — Verify + build (AC: #4)**
  - [ ] Update/replace any screenshots that no longer match (landing page from Story 12.8, nav from Epic 10, admin screens); run `pixi run docs-build` (strict) and fix broken links/nav.

## Dev Notes

### What changed since the first pass (drivers for this reconciliation)

- **Roles:** member / org-admin / **global-admin** (ADMIN-org tier, Story 2.8). Global admins are provisioned as admin of every org and oversee all orgs.
- **Create-org gating:** restricted to global admins (Story 2.12); the ADMIN org is hidden from the org switcher.
- **Admin toolkit:** add-existing-by-email (2.7), create-new-user (2.10), **promote** not transfer (2.16), **demote** admin→member (2.20), remove + last-admin rule (2.9).
- **Zero-org UX:** zero-org users are restricted to the home page until added (2.18); org switcher hidden for a single org (2.19).
- **Global-admin management screen:** list / grant-by-email / revoke (Story 13.1).
- Cross-check the shipped strings/labels (empty-state copy, error messages like "No registered user with that email", button labels "Make admin" / "Remove admin") against the final UI so the docs quote them accurately.

### Scope / coordination

- User-facing pages only (User Guide + How-To). API contract details go in **11.16**; developer/architecture details in **11.17**; README + general sweep in **11.18** — avoid overlap.
- This is the SECOND reconciliation pass. 11.11 covered the initial zero-org / add-by-email work; this pass adds the admin tier, promote/demote, create-org gating, and the global-admin screen.

### Project Structure Notes

- Docs under `docs/user-guide/` and `docs/how-to/`; nav in `mkdocs.yml`. Build gate: `pixi run docs-build` (`mkdocs build --strict`), part of `pixi run ci`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 11.15]
- Epic 2 stories: `2-7`, `2-8`, `2-9`, `2-10`, `2-12`, `2-16`, `2-18`, `2-19`, `2-20`; Story `13-1-global-admin-management-screen.md`
- Prior pass: `11-11-user-facing-documentation-reconciliation.md`
- Docs: `docs/user-guide/accounts-and-organizations.md`, `docs/how-to/manage-organization.md`

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Opus 4.8, 1M context)

### Debug Log References

- `pixi run docs-build` (`mkdocs build --strict`) — green.
- `pixi run ci` — green.

### Completion Notes List

- Verified all claims against the live backend (`users/views.py`, `services.py`, `urls.py`) and the shipped SPA components (`OrgSwitcher`, `NoOrgState`, `SideNav`, `HomePage`, `MembersPage`, `GlobalAdminsPage`, `Layout`).
- `accounts-and-organizations.md`: added the three-tier role table (member / org-admin / global-admin); documented the zero-org experience as **restricted to the home page** until an admin adds you (2.18); create-org **restricted to global admins** with the ADMIN org hidden from the switcher (2.12); single-org switcher hiding (2.19); replaced "hand over the admin role" with promote/demote (2.16/2.20); added a Global Admins management subsection (list / grant-by-email / revoke + last-global-admin guard, 13.1). Fixed the stale "dashboard" login destination.
- `manage-organization.md`: documented add-existing (with the "No registered user with that email" outcome) and create-new-user (2.10), promote/demote, remove + last-admin rule; removed all "transfer admin / stepped down automatically" wording; added the global-admin management how-to.
- Screenshots remain placeholders (no images are committed); captured the placeholder notes per the story rather than inventing images.

### File List

- `docs/user-guide/accounts-and-organizations.md`
- `docs/how-to/manage-organization.md`
</content>
