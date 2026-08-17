# Story 21.6: Organization and Member Management Pages

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.5**. Admin-gated by the `OrgAdminRequiredMixin` from Story 21.4.

## Story

As an org admin,
I want to manage my organisation and its members through server-rendered pages,
so that I can add, remove, and re-role members without the SPA.

## Acceptance Criteria

1. **The organisation hub is converted.**
   Given `OrganizationPage.tsx` is an admin-facing hub that links to members, API keys, and org creation
   rather than duplicating their logic (Story 2.11), when it is converted, then an admin-gated page presents
   the same destinations with the same composition-by-linking approach.
2. **Org creation is global-admin only.**
   Given Story 2.12 deliberately reversed self-service org creation and restricted it to **global** admins,
   when `CreateOrgDialog.tsx` is converted, then org creation is a crispy form gated by the
   `GlobalAdminRequiredMixin`, the affordance is **hidden** for non-global-admins, and the creating flow makes
   the intended admin the new org's admin.
3. **Member management actions are converted.**
   Given `MembersPage.tsx` supports adding an **existing** user by email (Story 2.7), creating a **new** user
   account on their behalf (Story 2.10), removing a member (FR-1.4), and promoting/demoting admin (Stories
   2.16, 2.20), when it is converted, then each action is a CSRF-protected POST calling the existing member
   services directly, and destructive actions require confirmation.
4. **New-member credentials are shown once.**
   Given an admin creates an account on a member's behalf and shares the credentials out-of-band (FR-1.3, no
   email infrastructure), when the account is created, then the temporary password is displayed **once** on
   the result page with an explicit "share out-of-band, it will not be shown again" warning, and it is not
   written to the session or any log.
5. **The last admin is protected.**
   Given an org must always retain at least one admin (FR-1.5) and Story 2.16 additionally protects global
   admins from demotion, when the last admin attempts self-demotion or removal, then the server rejects it
   with a form error and the membership is unchanged.
6. **Leaving an org does not delete it.**
   Given a non-owner member can leave an org (FR-1.7), when they do so, then the org survives, their access
   ends immediately, and they land on the zero-org state if it was their only membership.
7. **Gate green with authorisation coverage.**
   When the story completes, then tests cover add-existing, create-new, remove, promote, demote, last-admin
   protection, leave-org, non-admin denial, and cross-org denial, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — Organisation hub page (AC: #1)** — Admin-gated; links only.
- [ ] **Task 2 — Create-org form (AC: #2)** — Global-admin gated; affordance hidden otherwise.
- [ ] **Task 3 — Members list + add-existing + create-new (AC: #3, #4)** — Two distinct flows; one-time
  credential reveal for create-new.
- [ ] **Task 4 — Remove / promote / demote (AC: #3, #5)** — POST + confirm; last-admin and global-admin guards
  enforced in the service, not the template.
- [ ] **Task 5 — Leave org (AC: #6)**.
- [ ] **Task 6 — Tests + gate (AC: #7)**.

## Dev Notes

### Grounded facts (verified)

- Endpoints already present in `generate_sbom/users/urls.py`: `orgs/create/`, `orgs/members/`,
  `orgs/members/create-user/`, `orgs/members/<int:user_id>/`, `orgs/promote-admin/`, `orgs/demote-admin/`,
  `orgs/leave/`, `orgs/`, `orgs/me/`.
- `frontend/src/pages/OrganizationPage.tsx` header comment (Story 2.11): "one admin-facing place that gathers
  the org-administration destinations … It composes the existing management pages by linking to them rather
  than duplicating their logic." Preserve that.
- `frontend/src/pages/MembersPage.tsx` uses a `ToggleButtonGroup` for the member/admin role control.
- Prior stories: 2.3 (org administration), 2.5 (create org from UI), 2.7 (add/remove **existing** users by
  email), 2.8 (global-admin org + cross-org provisioning), 2.9 (membership edge cases), 2.10 (admin creates a
  **new** user account), 2.11 (org hub), 2.12 (**org creation restricted to global admins**), 2.16 (fix
  make-admin: promote, don't transfer; protect global admins), 2.20 (demote admin to member).

### Two distinct member flows — do not merge them

Story 2.7 adds an **existing** user by email; Story 2.10 creates a **new** account on the member's behalf.
They were separated deliberately (2.7 originally raised `no_such_user`, and 2.10 was reopened to restore
provisioning). Keep them as two form actions with distinct outcomes.

### Watch for

- **Promote ≠ transfer.** Story 2.16 fixed a bug where "Make admin" transferred rather than promoted. The
  service already encodes the correct behaviour — call it, do not reimplement.
- **Global admins are protected from demotion** (2.16).
- **`is_admin` is per-active-org** — an admin of org A managing org B's members must be refused.

### Testing standards

- Authorisation matrix per action: member, org admin, global admin, cross-org.
- A test asserting the temporary password appears exactly once and is absent from a subsequent page render.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.6: Organization and Member Management Pages]
- `frontend/src/pages/{OrganizationPage,MembersPage}.tsx`, `frontend/src/components/CreateOrgDialog.tsx`,
  `generate_sbom/users/{views,services,selectors}.py`.
- Upstream: `21-5-authentication-pages.md`.
- Architecture: AD-2 (org isolation), AD-14 (org/admin/auth model).

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
