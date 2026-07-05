# Story 2.7: Admin Adds/Removes Existing Users by Email

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an org admin,
I want to add existing users to my org by email and remove them,
so that I control who is a member.

## Acceptance Criteria

1. **Add existing user by email.** The current "Add member" flow creates a brand-new user with a temp password. Change the primary flow to **add an existing user by email** (looked up by email). If no registered user matches, return a clear error (no auto-create for now). Admin-gated (403 for non-admins / non-global-admins).
2. **Remove member.** An admin can remove a member from the org (existing remove flow), respecting the Story 2.9 edge rules. Removing a user from their **only** org drops them to the zero-org state (Story 2.6).
3. **Members page + tests.** The Members page exposes add-existing-by-email + remove for admins, with tests: add existing, add-nonexistent error, remove, permission-gating.

## Tasks / Subtasks

- [ ] **Task 1 — Backend: add existing user by email (AC: #1)**
  - [ ] Rewrite `create_member()` (`backend/generate_sbom/users/services.py:124-138`): look up the user by email (case-insensitive, as it does now); if **not found**, raise a new `NoSuchUserError(MembershipError)` (e.g. `code="no_such_user"`, message "No registered user with that email.") instead of `create_user(...)`. Keep the `AlreadyMemberError` path. Drop the `temp_password` parameter.
  - [ ] Update `AddMemberSerializer` (`serializers.py:44-48`): remove `temp_password`; keep `email`.
  - [ ] Update `MembersView.post()` (`views.py:217-233`): call `create_member(org, email)` without a temp password; the existing `_membership_error` path returns the new error as a 400 envelope. Keep admin-gating via `get_admin_org` (403).
- [ ] **Task 2 — Backend: remove member (AC: #2)**
  - [ ] `remove_member()` (`services.py:141-149`) and `MemberDetailView.delete()` (`views.py:236-254`) already exist. Confirm they satisfy the Story 2.9 edge rules (sole-admin protection) — coordinate with 2.9. Removing the user's last membership already leaves them zero-org (nothing extra to do given Story 2.6).
- [ ] **Task 3 — Frontend: Members page (AC: #3)**
  - [ ] `MembersPage` (`frontend/src/pages/MembersPage.tsx`): the "Add a member" form currently has Email + **Temp password** fields and calls `addMember(email, password)`. Remove the password field; `handleAdd` calls `addMember(email)`.
  - [ ] `addMember` client (`frontend/src/api/orgs.ts:41`): drop `tempPassword`; body `{ email }`.
  - [ ] Update the add-failure message to distinguish "no such user" (surface the backend `error`) from "already a member". The remove/transfer UI (`handleRemove`, `handleTransfer`) is unchanged.
- [ ] **Task 4 — Tests (AC: #3)**
  - [ ] Backend (`backend/tests/unit/test_membership.py`): add-existing-by-email succeeds; add-nonexistent-email returns the `no_such_user` 400; add-already-member returns `already_member`; remove works; non-admin gets 403. **Update** existing add-member tests that pass a `temp_password` and expect auto-create.
  - [ ] Frontend (`MembersPage` test): add-by-email calls `addMember(email)`; the no-such-user error renders.

## Dev Notes

### Behavior change: no more auto-create

The existing `create_member` (`services.py:124-138`) does find-or-**create** with a temp password — that is exactly what AC #1 removes. New model: an admin can only add someone who has already registered. This is the single most important change; do not leave the create-user fallback in.

- Add-member endpoint contract: `POST /orgs/members/` now takes `{ "email": ... }` only. On unknown email → `{ "error": "...", "code": "no_such_user" }` 400.
- Admin-gating is already enforced server-side via `get_admin_org` (`auth.py:58`). **Story 2.8** makes global admins count as admins everywhere (they get real admin memberships), so `get_admin_org` needs no special-casing here — but the "non-global-admins" wording in AC #1 depends on 2.8 being in place.

### Frontend current state

`MembersPage.tsx` (read in full): admin-only "Add a member" `Paper` with Email + Temp-password `TextField`s, `handleAdd` → `addMember(email, password)`; members table with Remove / Make-admin actions gated on `isAdmin`. `PageState` (`EmptyState`/`ErrorState`/`LoadingState`) components already used — reuse them.

### Cross-story dependencies

- **Story 2.6** — zero-org state (removing last membership drops to it). No extra code here.
- **Story 2.8** — global-admin gating semantics for AC #1's "non-global-admins".
- **Story 2.9** — sole-admin / edge rules for AC #2's remove flow. Recommended order: 2.8 and 2.9 before or alongside 2.7.

### Testing standards

- Backend: pytest `@pytest.mark.django_db`, DRF `APIClient`, `backend/tests/unit/test_membership.py`. Frontend: Vitest + RTL, mock `../api/orgs` with `vi.mock`, no MSW.

### Project Structure Notes

- Backend `backend/generate_sbom/users/{services,serializers,views}.py`. Frontend `frontend/src/pages/MembersPage.tsx`, `frontend/src/api/orgs.ts`. No model/migration change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.7: Admin Adds/Removes Existing Users by Email] (lines 589-612)
- Backend: `backend/generate_sbom/users/services.py:124`, `serializers.py:44`, `views.py:217`
- Frontend: `frontend/src/pages/MembersPage.tsx:41`, `api/orgs.ts:41`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
