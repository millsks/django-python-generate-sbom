# Story 2.10: Admin Creates a New User Account (Restore New-User Provisioning)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an org admin,
I want to create a brand-new user account and add it to my org in one step,
so that I can onboard someone who has not registered yet, instead of only adding
people who already have an account.

## Acceptance Criteria

1. **Restore new-user provisioning (distinct action).** An admin can **create a
   brand-new user** (email + a temporary password shared out-of-band) **and** add
   them to the active org in one action. This is a **separate** action from Story
   2.7's "add an existing user by email" — both coexist on the Members page. There
   is no email infrastructure, so the prior model applies: the admin sets a temp
   password and communicates it to the new user out-of-band.
2. **Keep add-existing-by-email intact.** The existing add-existing flow (Story 2.7)
   and its `no_such_user` error are unchanged: the "add existing" action still
   raises `no_such_user` when the email is not registered. Only the new "create"
   action provisions an account.
3. **Duplicate-email handling.** Creating a user whose email is already registered
   returns a clear error (does **not** silently create a duplicate or fall through
   to adding the existing user) — the admin is told to use "add existing" instead.
4. **Admin-gated.** Both actions are admin-gated (org admin OR global admin) — a
   non-admin receives a 403.
5. **Tested.** Backend and frontend tests cover: create-new-user succeeds and adds
   the membership; duplicate-email is rejected; add-existing still works and still
   raises `no_such_user`; permission gating (403 for non-admins).

## Tasks / Subtasks

- [ ] **Task 1 — Backend: create-user service (AC: #1, #3)**
  - [ ] Add a new service `create_member_user(org, email, temp_password, role=Role.MEMBER)` in `backend/generate_sbom/users/services.py` (next to `create_member`, `services.py:223-238`). It creates the account **and** the membership atomically (`@transaction.atomic`): if a user with that email already exists (`User.objects.filter(email__iexact=email).exists()`), raise a new `EmailTakenError(MembershipError)` (`code="email_taken"`, message "A user with that email already exists — add them as an existing member instead."); otherwise `User.objects.create_user(email=email, password=temp_password)` then `OrgMembership.objects.create(org=org, user=user, role=role)`. Log `member_created`. Do **not** modify `create_member` — it must keep raising `NoSuchUserError` (Story 2.7 contract, AC #2).
  - [ ] Register `EmailTakenError` alongside the other `MembershipError` subclasses (`services.py:114-146`).
- [ ] **Task 2 — Backend: serializer + endpoint (AC: #1, #4)**
  - [ ] Add `CreateMemberUserSerializer` in `serializers.py` (next to `AddMemberSerializer`, `serializers.py:44-48`): `email = EmailField()`, `temp_password = CharField(write_only=True, min_length=8)`.
  - [ ] Add a `CreateMemberUserView` in `views.py` (or a `create-user` mode on `MembersView.post`, `views.py:260-272`) mapped to `POST /orgs/members/create-user/`. Admin-gate via `get_admin_org(request)` (403 → `_NOT_ADMIN`) exactly like `MembersView.post`. Call `create_member_user(org, email, temp_password)`; on `MembershipError` return `_membership_error(exc)` (the `email_taken` code surfaces as a 400 envelope). Return `201` with `{ "user_id": user.pk, "email": user.email }`.
  - [ ] Wire the route in the users app URLconf next to the existing `orgs/members/` route (find where `MembersView`/`MemberDetailView` are registered).
- [ ] **Task 3 — Frontend: Members page (AC: #1, #2)**
  - [ ] `MembersPage` (`frontend/src/pages/MembersPage.tsx`): the admin-only "Add a member" `Paper` (`MembersPage.tsx:140-164`) currently has one email form → `addMember(email)`. Add a **second, clearly-labelled action** to create a new user: an email + temp-password form (or a toggle between "Add existing" and "Create new") that calls the new client. Keep the existing `handleAdd`/`addMember(email)` path and its `no_such_user` / `already_member` error mapping (`MembersPage.tsx:44-60`) intact. Add an `email_taken` error message for the create path.
  - [ ] `frontend/src/api/orgs.ts`: add `createMemberUser(email, tempPassword)` → `POST /orgs/members/create-user/` with body `{ email, temp_password }` (mirror `addMember`, `orgs.ts:41-46`). Leave `addMember` unchanged.
- [ ] **Task 4 — Tests (AC: #5)**
  - [ ] Backend (`backend/tests/unit/test_membership.py`): create-new-user succeeds and creates the membership; create with an already-registered email returns the `email_taken` 400; create is 403 for a non-admin; **regression**: add-existing (`create_member`) still raises `no_such_user` for an unknown email.
  - [ ] Frontend (`frontend/src/pages/MembersPage.test.tsx`): create-new-user calls `createMemberUser(email, tempPassword)` and reloads; the `email_taken` error renders; the existing add-by-email path is unchanged.

## Dev Notes

### Why this story exists (the gap)

Story 2.7 deliberately removed the old find-**or-create** behavior from `create_member`
— it now raises `NoSuchUserError` instead of provisioning an account (`services.py:231-233`).
That is correct for "add existing", but it removed the **only** way an admin could
onboard a brand-new person. This story restores new-user provisioning as an **explicit,
separate** action so both flows coexist: "add existing by email" (2.7) and "create a
new account" (this story). Do **not** reintroduce auto-create into `create_member`.

### No email infrastructure → temp password out-of-band

There is no transactional email in the system, so follow the pre-2.7 model: the admin
supplies a temporary password (validated `min_length=8`, `write_only`) and shares it
with the user out-of-band. Do not attempt to email or auto-generate/return the password
in a way that logs it — never log the plaintext password.

### Contract

- New endpoint: `POST /orgs/members/create-user/` body `{ "email": ..., "temp_password": ... }`.
  On duplicate email → `{ "error": "...", "code": "email_taken" }` 400. On success → `201`
  `{ "user_id": ..., "email": ... }`.
- Existing endpoint unchanged: `POST /orgs/members/` body `{ "email": ... }`, unknown email →
  `{ "code": "no_such_user" }` 400 (Story 2.7).
- Admin-gating already flows through `get_admin_org` (`auth.py`); global admins count as org
  admins everywhere (Story 2.8), so no special-casing is needed.

### Cross-story dependencies

- **Story 2.7** — the add-existing flow this story sits beside; its `no_such_user` contract
  must stay intact (AC #2). Recommended: 2.7 merged before this story.
- **Story 2.8** — global admins are treated as org admins for the AC #4 gating.
- **Story 2.11** — the org-maintenance nav that surfaces the Members page (both actions) as a
  control-center entry; independent but complementary.

### Testing standards

- Backend: pytest `@pytest.mark.django_db`, DRF `APIClient`, `backend/tests/unit/test_membership.py`.
- Frontend: Vitest + RTL, mock `../api/orgs` with `vi.mock`, no MSW (mirror `MembersPage.test.tsx`).

### Project Structure Notes

- Backend `backend/generate_sbom/users/{services,serializers,views}.py` + the users URLconf.
- Frontend `frontend/src/pages/MembersPage.tsx`, `frontend/src/api/orgs.ts`.
- No model or migration change — `User.objects.create_user` and `OrgMembership` already exist.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.10: Admin Creates a New User Account]
- Backend: `backend/generate_sbom/users/services.py:223` (`create_member`), `serializers.py:44` (`AddMemberSerializer`), `views.py:260` (`MembersView.post`)
- Frontend: `frontend/src/pages/MembersPage.tsx:140`, `frontend/src/api/orgs.ts:41`
- Related stories: `2-7-admin-add-remove-existing-users-by-email.md`, `2-8-global-admin-org-and-cross-org-provisioning.md`, `2-11-org-maintenance-navigation-for-admins.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
