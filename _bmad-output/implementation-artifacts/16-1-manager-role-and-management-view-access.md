# Story 16.1: Manager Role & Management-View Access

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **First story of Epic 16 — build it first.** It introduces the `MANAGER` role, the promote/demote
> services, the server-side management-view gate, the `ManagerRoute` guard, and the `auth/me` capability
> that Stories 16.2, 16.3, and 16.4 all reuse. Reuses the Story 2.16 (`promote_member_to_admin`) / 2.20
> (`demote_admin_to_member`) service pattern and the Story 2.17 route-guard + API-authorization pattern.
> **Full Epic 16 build order: 16.1 → 16.2 → 8.26 → 16.3 → 16.4.**

## Story

As an org admin,
I want to promote a member to a **manager** who can see the management views,
so that I can delegate read-level oversight of the org's results without granting member-management powers.

## Acceptance Criteria

1. **`MANAGER` role added.**
   Given `OrgMembership.Role` currently has `ADMIN`/`MEMBER` (`users/models.py:92-98`, `role`
   `max_length=10`), when the change lands, then a third value `MANAGER = "manager", "Manager"` is added
   (`"manager"` is 7 chars — fits `max_length=10`, no width change) with a generated Django migration
   (choice-only `AlterField`).
2. **Additive tier — admins and global admins inherit management-view access.**
   Given the management views, when access is evaluated, then a caller is granted access iff their role in
   the active org ∈ {`manager`, `admin`} **OR** they are a global admin. Manager is an **additive** tier
   *below* admin: an org admin (and a global admin) automatically has management-view access **without**
   being assigned the `manager` role. (Rationale: management views are a strict subset of what an admin can
   already see; requiring an explicit manager role for admins would be a regression.)
3. **Managers gain NO member-management powers.**
   Given a manager, when they act, then they get the management **views only** (Epic 16.2/16.3) — they
   **cannot** promote/demote/add/remove members, create orgs, or reach any admin-only endpoint. The manager
   tier is view-access, not membership authority.
4. **Org-admin promote/demote.**
   Given an **org admin** of the org, when they promote a member, then `promote_member_to_manager(org, target)`
   sets that org's membership role to `MANAGER` (raises `NotAMemberError` if not a member; idempotent if
   already manager); `demote_manager_to_member(org, target)` sets it back to `MEMBER`. Both are **admin-gated**
   (mirroring 2.16/2.20). Promote/demote does not touch any other org or the global tier. A manager cannot
   promote/demote (AC #3).
5. **`auth/me` exposes the capability.**
   Given the SPA needs to gate the nav/route, when `auth/me` is called (`users/views.py:142-155`), then the
   response gains a management-view capability flag — e.g. `is_manager` meaning **role ∈ {manager, admin} OR
   global-admin** in the active org (the additive rule of AC #2, computed server-side). `is_admin` /
   `is_global_admin` are unchanged.
6. **`ManagerRoute` + server-side API gating.**
   Given a management page, when a non-manager types its URL, then a `ManagerRoute` guard (built like
   `AdminRoute`, `frontend/src/components/AdminRoute.tsx`, but gated on the `isManager` capability) redirects
   them, **and** the management endpoints enforce the same rule server-side (403) — nav hiding is not the gate
   (Story 2.17 rule). A management nav entry is shown only when `isManager`.
7. **MembersPage actions.**
   Given the MembersPage (`frontend/src/pages/MembersPage.tsx:175-180`, which has "Make admin"/"Make member"),
   when an admin views a member, then it gains **"Make manager"** / **"Make member"** actions calling the new
   promote/demote endpoints, consistent with the existing promote/demote UI. Shown to admins only.
8. **Tested; CI green.**
   Backend + frontend tests per the Tasks; `pixi run ci` green.

## Acceptance Criteria — the additive rule, stated precisely

`is_manager` (management-view access) ⇔ `role == manager` **OR** `role == admin` **OR** `is_global_admin`.
`is_admin` (member-management authority) ⇔ `role == admin` **OR** `is_global_admin` (unchanged).
So every admin is a manager-for-view-purposes, but a manager is **not** an admin.

## Tasks / Subtasks

- [ ] **Task 1 — Role + migration (AC: #1)**
  - [ ] Add `MANAGER = "manager", "Manager"` to `OrgMembership.Role` (`backend/generate_sbom/users/models.py:92`).
    Generate the `manifests`… no — the `users` migration (choice-only `AlterField` on `role`; `max_length=10`
    already fits `"manager"`).
- [ ] **Task 2 — Promote/demote services + endpoints (AC: #4, #3)**
  - [ ] `services.py`: `promote_member_to_manager(org, target)` and `demote_manager_to_member(org, target)` —
    mirror `promote_member_to_admin` (`users/services.py:333`) / `demote_admin_to_member` (`:353`): set only
    that org's membership `role`; `NotAMemberError` if not a member; idempotent; **no** other-org or global
    writes. A demote of a manager returns them to `MEMBER` only (never touches an admin's role).
  - [ ] Views/urls: `POST /api/v1/orgs/promote-manager/` and `POST /api/v1/orgs/demote-manager/` (both
    **admin-gated** via `get_admin_org`, like `PromoteAdminView`), returning **204**. Reuse `UserIdSerializer`.
- [ ] **Task 3 — The management-view capability + server gate (AC: #2, #5, #6)**
  - [ ] `services.py`: `has_management_access(request|user, org) -> bool` = role ∈ {manager, admin} OR
    `is_global_admin(user)` (the additive rule). Compute against the **active** org (same source `auth/me`'s
    `is_admin` uses, `get_admin_org`). This single predicate is the server-side gate for every Epic 16
    management endpoint (16.2/16.3 import it; 16.4 uses the stricter admin gate).
  - [ ] `AuthMeView.get` (`users/views.py:142-155`): add `"is_manager": has_management_access(...)` to the
    payload next to `is_admin`/`is_global_admin`.
- [ ] **Task 4 — Frontend capability, route guard, nav (AC: #6, #7)**
  - [ ] `AuthProvider` (`frontend/src/auth/AuthProvider.tsx`): add `isManager` alongside `isAdmin`/
    `isGlobalAdmin` (set from `me.is_manager`, `:68-69`), expose it in the context value (`:97`) and the
    `AuthContextValue` type (`:19-20`).
  - [ ] New `frontend/src/components/ManagerRoute.tsx` (+ test) modeled on `AdminRoute.tsx` but gated on
    `isManager`. Wire the management routes in `App.tsx` under it.
  - [ ] A management nav entry (SideNav) shown only when `isManager`.
  - [ ] `frontend/src/api/orgs.ts`: `promoteManager(userId)` / `demoteManager(userId)`. `MembersPage`
    (`:175-180`): add "Make manager" (→ `promoteManager`) and, for a manager, "Make member" (→ `demoteManager`),
    admin-only, alongside the existing admin actions.
- [ ] **Task 5 — Tests (AC: #8)**
  - [ ] Backend: `promote_member_to_manager` sets role=manager without other-org/global writes; idempotent;
    `NotAMemberError` for a non-member; `demote_manager_to_member` returns to member; endpoints 403 for a
    non-admin caller. `has_management_access`: true for manager, admin, and global-admin; false for a plain
    member. `auth/me` returns `is_manager` per the additive rule (manager→true, admin→true, global-admin→true,
    member→false). A manager is blocked (403) from every admin-only endpoint (no member-management powers).
  - [ ] Frontend (Vitest + RTL): `ManagerRoute` redirects a non-manager and renders for a manager/admin;
    MembersPage "Make manager"/"Make member" call the new endpoints; nav entry shows only when `isManager`.
  - [ ] `pixi run ci` green.

## Dev Notes

### Design decisions (product owner)

- **Additive tier (the core rule).** Manager sits **between** member and admin. Access to a management view is
  granted to `manager`, `admin`, **and** global-admin — org admins and global admins *inherit* management-view
  access and do **not** need the explicit `manager` role. This is deliberately additive (a superset by
  seniority), so the gate is a single OR predicate, not a role-equality check.
- **Views only, no authority.** A manager gets the two management views (16.2 tree/rollup, 16.3 consolidated
  SBOM) and nothing else — explicitly **no** promote/demote/add/remove, no org creation, no admin endpoints.
  Every existing admin-only endpoint stays admin-gated; managers 403 on them.
- **Promote/demote is an org-admin action.** Only an org admin (or global admin, who is admin everywhere)
  promotes a member to manager or demotes a manager to member — mirroring exactly how 2.16/2.20 gate the
  admin promote/demote. A manager cannot manage roles.
- **Merge-tiering preview (context for 16.3/16.4, not built here):** a *manager* can later merge results only
  **within a single Application ID** (16.3); an *admin* can arbitrarily multi-select results across App IDs
  (16.4). That capability split is enforced in those stories; 16.1 only establishes the role + view gate.

### Current state (verified)

- Roles: `OrgMembership.Role` = ADMIN/MEMBER, `role` `CharField(max_length=10)`
  (`backend/generate_sbom/users/models.py:92-98`).
- Promote/demote precedent: `promote_member_to_admin` (`users/services.py:333`), `demote_admin_to_member`
  (`:353`); admin-gated views like `PromoteAdminView` returning 204 (Story 2.16).
- `auth/me`: `AuthMeView.get` returns `{id?, email?, is_admin, is_global_admin, ...}`
  (`users/views.py:142-155`); `is_admin = get_admin_org(request) is not None`, `is_global_admin = is_global_admin(user)`.
- Frontend: `AuthProvider` exposes `isAdmin`/`isGlobalAdmin` (`frontend/src/auth/AuthProvider.tsx:19-20,41-42,68-69,97`);
  `AdminRoute`/`GlobalAdminRoute` guards (`frontend/src/components/`); `MembersPage` "Make admin"/"Make member"
  (`frontend/src/pages/MembersPage.tsx:107-120,175-180`); `api/orgs.ts` `promoteAdmin`/`demoteAdmin`.

### Testing standards

- Backend: pytest `@pytest.mark.django_db`, DRF `APIClient`, reuse the org/membership fixtures from the
  Story 2.16/2.20 tests. Frontend: Vitest + RTL, mock the api module with `vi.mock`, wrap in `MemoryRouter`
  (mirror `AdminRoute.test.tsx`).

### Project Structure Notes

- Backend: `users/{models,services,views,urls,serializers}.py` + a `users` migration + tests.
- Frontend: new `ManagerRoute.tsx` (+ test), `AuthProvider` capability, SideNav entry, `App.tsx` wiring,
  `api/orgs.ts` + `MembersPage` actions + tests. No new model beyond the role choice.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.1: Manager Role & Management-View Access]
- `backend/generate_sbom/users/models.py:92-98` (Role), `users/services.py:333,353` (promote/demote precedent),
  `users/views.py:142-155` (`AuthMeView`), `PromoteAdminView` (2.16)
- `frontend/src/components/AdminRoute.tsx` (guard pattern), `frontend/src/auth/AuthProvider.tsx:19-20,68-69,97`,
  `frontend/src/pages/MembersPage.tsx:107-120,175-180`, `frontend/src/api/orgs.ts`
- Related: `2-16-fix-make-admin-and-protect-global-admin.md`, `2-20-demote-admin-to-member.md`,
  `2-17-admin-route-and-api-authorization.md`, `13-1-global-admin-management-screen.md`
- Downstream: `16-2-application-id-rollup-view.md`, `16-3-consolidated-sbom-by-application-id.md`,
  `16-4-admin-multi-select-consolidated-sbom.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
