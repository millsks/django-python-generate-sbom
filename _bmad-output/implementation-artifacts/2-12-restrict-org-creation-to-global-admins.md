# Story 2.12: Restrict Organization Creation to Global Admins (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the product owner,
I want only global admins (members of the ADMIN org) to create organizations,
so that org provisioning is centrally controlled and regular users can't self-provision orgs.

## Acceptance Criteria

1. **Backend gate (403 for non-global-admins).** `POST /orgs/create/` is rejected with
   **403** and code `not_global_admin` when the caller is **not** a global admin (a regular
   user or an ordinary org-admin) — **no org is created**. When the caller **is** a global
   admin the org is created as today (**201**). The gate uses `services.is_global_admin`
   (already imported in `views.py`), matching how `GrantGlobalAdminView` gates
   (`views.py:136-137`).
2. **`auth/me` exposes global-admin status.** `GET /api/v1/auth/me/` includes an
   **`is_global_admin`** boolean, and `AuthProvider` exposes it via `useAuth` (a new field on
   `AuthValue`). This extends the **same** endpoint + provider surface as Story 10.5 —
   coordinate so both signals land together (see Cross-story coordination below).
3. **Frontend hides create-org affordances for non-global-admins.** For a non-global-admin
   user (including a zero-org user), **all** create-org affordances are hidden:
   - `NoOrgState` — the "Create organization" button (`NoOrgState.tsx:21-26`).
   - `OrgSwitcher` — the zero-org "Create organization" button (`OrgSwitcher.tsx:46-58`)
     **and** the "New organization" `Select` menu item (`OrgSwitcher.tsx:88-91`).
   - `OrganizationPage` — the "New organization" create-org card (`OrganizationPage.tsx:72-87`).
   A zero-org non-admin sees an "ask an admin to add you" empty state with **no** create button.
4. **Global admin still sees create.** For a global admin the create-org affordances remain
   available and functional on all the above surfaces.
5. **ADMIN org hidden from the switcher.** The system ADMIN org (`is_admin_org=True`) is **not**
   shown as a selectable org in the org switcher / org list — it's a system org, not a workspace.
   Filter it out of the org-listing path (`get_user_orgs` / `OrgListView`). A full global-admin
   management screen (grant/revoke, ADMIN-org membership) is **out of scope here** — deferred to a
   later story.
6. **Tested.** Backend: non-global-admin create → 403 (`not_global_admin`, no org created);
   global admin → 201; the ADMIN org is excluded from the org list. Frontend: each affordance
   hidden for a non-global-admin and shown for a global admin.

## Tasks / Subtasks

- [ ] **Task 1 — Gate `CreateOrgView` on global admin (AC: #1, #5)**
  - [ ] `backend/generate_sbom/users/views.py`: in `CreateOrgView.post` (`views.py:242-248`),
    before validating/creating, check `if not is_global_admin(cast(User, request.user)):` and
    return `Response(_NOT_GLOBAL_ADMIN, status=status.HTTP_403_FORBIDDEN)`. `is_global_admin` and
    the `_NOT_GLOBAL_ADMIN` envelope (`views.py:48`) already exist and are used by
    `GrantGlobalAdminView` (`views.py:136-137`) — reuse them; do not add a new code or import.
  - [ ] Keep the existing `create_org(...)` call for the global-admin path unchanged.
- [ ] **Task 2 — Add `is_global_admin` to `auth/me` (AC: #2)**
  - [ ] `backend/generate_sbom/users/views.py`: in `AuthMeView.get` (`views.py:120-123`), add
    `"is_global_admin": is_global_admin(user)` to the response dict. Update the docstring, which
    currently says global-admin info is "deliberately omitted here (deferred to a later story)"
    (`views.py:117-118`) — this is that story.
  - [ ] `frontend/src/api/auth.ts`: extend `CurrentUser` (`auth.ts:10-13`) with
    `is_global_admin: boolean` so `getMe()` returns it.
- [ ] **Task 3 — Expose `isGlobalAdmin` from `AuthProvider` (AC: #2)**
  - [ ] `frontend/src/auth/AuthProvider.tsx`: `refresh()` already calls `getMe()` and discards the
    result (`AuthProvider.tsx:37`). Capture it, store `isGlobalAdmin` in state, and add
    `isGlobalAdmin: boolean` to `AuthValue` (`AuthProvider.tsx:13-19`) and the memoized `value`
    (`AuthProvider.tsx:76-79`). Reset it to `false` in the `catch` (anon) and `logout` paths.
    **Coordinate with Story 10.5**, which also captures the `getMe()` result (for `user`) on this
    exact line — implement both together to avoid a conflict; a single `const me = await getMe()`
    feeds both `user` and `isGlobalAdmin`.
- [ ] **Task 4 — Hide create-org affordances (AC: #3, #4)**
  - [ ] `frontend/src/components/NoOrgState.tsx`: gate the "Create organization" `Button`
    (`NoOrgState.tsx:21-26`) on `useAuth().isGlobalAdmin`; when false, render the empty state with
    no `action` (the `NO_ORG_MESSAGE` already says "create one **or** ask an admin to add you" —
    for a non-admin, the create half is simply unavailable). Consider tightening the message copy
    so a non-admin isn't told to "create one" when they can't.
  - [ ] `frontend/src/components/OrgSwitcher.tsx`: gate the zero-org create `Button`
    (`OrgSwitcher.tsx:46-58`) and the `CREATE_ORG_VALUE` "New organization" `MenuItem`
    (`OrgSwitcher.tsx:88-91`) on `isGlobalAdmin`. A non-admin zero-org user renders no switcher
    affordance (or a disabled/empty state) instead of a create button.
  - [ ] `frontend/src/pages/OrganizationPage.tsx`: gate the "New organization" `Card`
    (`OrganizationPage.tsx:72-87`) on `isGlobalAdmin`. Members/API-keys cards remain (they are
    admin-gated separately by their own pages).
- [ ] **Task 5 — Tests (AC: #5)**
  - [ ] Backend (`backend/generate_sbom/users/tests/`): extend the create-org view tests —
    non-global-admin authenticated user → 403 `not_global_admin` and org count unchanged; global
    admin → 201 and org created. Use the existing global-admin/ADMIN-org fixtures (Story 2.8).
  - [ ] Backend: assert `auth/me` returns `is_global_admin` true for a global admin, false otherwise.
  - [ ] Frontend: `NoOrgState.test.tsx`, `OrgSwitcher.test.tsx`, `OrganizationPage.test.tsx` —
    with `useAuth` mocked `isGlobalAdmin: false`, the create affordance is absent; with `true`, present.
- [ ] **Task 6 — Hide the ADMIN org from the org list (AC: #5, #6)**
  - [ ] `backend/generate_sbom/users/selectors.py`: `get_user_orgs` (`selectors.py:10-13`) returns
    every org the user belongs to, including the ADMIN org. Filter out `is_admin_org=True` so the
    ADMIN org never appears in `OrgListView` (`/orgs/`, which the switcher calls via `getOrgs()`).
    Also verify `get_request_org`'s active-org fallback doesn't default a global admin into the ADMIN org.
  - [ ] Test: a global admin's `/orgs/` response excludes the ADMIN org while still listing the normal
    orgs they were provisioned into.

## Dev Notes

### Why this story exists (the bug / policy reversal)

Stories 2.5/2.6 shipped **self-service** org creation: any authenticated user (including a
zero-org user) can `POST /orgs/create/`, and the UI offers "Create organization" in four
places. A user-reported issue plus a **confirmed policy decision** reverse this: **only global
admins** may create orgs. This is a deliberate reversal, not a regression — a zero-org
non-admin now waits to be added by an admin (Story 2.7 add-by-email) instead of
self-provisioning.

### What "global admin" means (reuse, don't reinvent)

A global admin is a member of the ADMIN org (`Org.is_admin_org=True`), introduced in Story 2.8.
`services.is_global_admin(user) -> bool` (`services.py:27`) is the single source of truth and is
already imported into `views.py` and used by `GrantGlobalAdminView` (`views.py:136-137`). Gate on
it; do **not** conflate with `isAdmin` (ordinary org-admin) — an org-admin who is not a global
admin must **not** be able to create orgs.

### Current shipped state (verified)

- `CreateOrgView.post` (`views.py:242-248`) creates an org for **any** authenticated caller — no
  global-admin check.
- `AuthMeView.get` (`views.py:120-123`) returns only `{id, email}`; its docstring explicitly
  defers global-admin info to "a later story" — this one.
- `AuthProvider.refresh()` calls `await getMe()` (`AuthProvider.tsx:37`) and discards the result.
- Create-org affordances live in: `NoOrgState.tsx:21-26`, `OrgSwitcher.tsx:46-58` and `:88-91`,
  `OrganizationPage.tsx:72-87`.

### Cross-story coordination (2.12 ↔ 10.5)

Both stories extend **`GET /api/v1/auth/me/`** and **`AuthProvider`**:
- **2.12** adds `is_global_admin` (backend response + `isGlobalAdmin` on `AuthValue`).
- **10.5** captures the `getMe()` user and adds `user` to `AuthValue`.
Both touch `AuthProvider.tsx:37` (the discarded `getMe()` call) and the `AuthValue` interface
(`AuthProvider.tsx:13-19`). Implement them together (or land one, then rebase the other) so a
single `const me = await getMe()` feeds both `user` and `isGlobalAdmin`. Note the dependency in
both story files. If 10.5 lands first, 2.12 only adds the `is_global_admin` field alongside the
already-captured `user`.

### Also folded in: hide the ADMIN org from the switcher (global-admin UX)

Per a confirmed decision, this story also **hides the system ADMIN org from the org switcher** (it's a
meta/system org, not a switchable workspace — see AC #5 / Task 6). This is why the operator "didn't see
the ADMIN org in the dropdown" originally being surprising: `get_user_orgs` returns it today. A dedicated
global-admin **management screen** (grant/revoke global admin, manage ADMIN-org membership) is
**deferred** to a later story — `POST /api/v1/admin/global-admins/` already exists as its backend.

### Testing standards

- Backend: pytest + DRF `APIClient`, reuse the ADMIN-org / global-admin fixtures from Story 2.8's
  tests; assert status codes and `Org` count deltas. Mirror `tests/unit` / existing view tests.
- Frontend: Vitest + RTL; mock `../auth/AuthProvider` `useAuth` with an `authState({ isGlobalAdmin })`
  helper (see `Layout.test.tsx`'s pattern). Wrap in `MemoryRouter` where components use router links.

### Project Structure Notes

- Backend: `backend/generate_sbom/users/views.py` (`CreateOrgView`, `AuthMeView`) + tests.
- Frontend: `frontend/src/api/auth.ts`, `frontend/src/auth/AuthProvider.tsx`,
  `frontend/src/components/NoOrgState.tsx`, `frontend/src/components/OrgSwitcher.tsx`,
  `frontend/src/pages/OrganizationPage.tsx` (+ their tests).
- No new dependency, no migration (global-admin is derived from existing ADMIN-org membership).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.12: Restrict Organization Creation to Global Admins (Bugfix)]
- Backend: `backend/generate_sbom/users/views.py:242` (`CreateOrgView`), `:120` (`AuthMeView`),
  `:48` (`_NOT_GLOBAL_ADMIN`), `:136` (gating precedent); `backend/generate_sbom/users/services.py:27`
  (`is_global_admin`)
- Frontend: `frontend/src/auth/AuthProvider.tsx:13,37,76`; `frontend/src/api/auth.ts:10`;
  `frontend/src/components/NoOrgState.tsx:21`; `frontend/src/components/OrgSwitcher.tsx:46,88`;
  `frontend/src/pages/OrganizationPage.tsx:72`
- Related stories: `2-5-create-organization-from-the-ui.md`, `2-6-zero-org-users-and-identity-decoupling.md`,
  `2-7-admin-add-remove-existing-users-by-email.md`, `2-8-global-admin-org-and-cross-org-provisioning.md`,
  `2-11-org-maintenance-navigation-for-admins.md`, `10-5-account-menu-shows-logged-in-user.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
