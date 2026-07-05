# Story 2.17: Route + API Authorization for Admin Pages (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a security-conscious operator,
I want admin-only pages enforced at the route and the API, not just hidden in the nav,
so that a non-admin can't reach them by typing the URL or calling the endpoint.

## Acceptance Criteria

1. **Route guard.** `/members` and `/organization` are gated by an `AdminRoute`: loading → nothing; anonymous → `/login` (preserving the intended location); an authenticated non-admin → redirected to `/`. Nav-hiding is no longer the only control.
2. **API authorization.** `GET /api/v1/orgs/members/` (the roster) is admin-only — returns **403 `not_admin`** for a non-admin (reverses Story 2.3's "any member can list"; Members is now an admin page).
3. **Single source of admin truth.** `GET /auth/me/` returns `is_admin` (admin of the active org) alongside `is_global_admin`; `AuthProvider` exposes `isAdmin` from that call, so the client never probes an admin-only endpoint to learn its role (no fragile 403-catch). `KeysPage` and `MembersPage` read `isAdmin` from `useAuth`.
4. **Tested.** A non-admin routed to `/members`/`/organization` is redirected; `AdminRoute` renders for admins; `MembersView.get` → 403 for non-admin / 200 for admin; `auth/me` carries `is_admin`.

## Tasks / Subtasks

- [ ] **Task 1 — Frontend admin route guard (AC: #1)**
  - [ ] `components/AdminRoute.tsx`: loading → null; anon → `<Navigate to="/login" state={{from}}>`; authed non-admin → `<Navigate to="/">`; admin → children. Apply to `/members` and `/organization` in `App.tsx`.
- [ ] **Task 2 — Backend authorization (AC: #2)**
  - [ ] Gate `MembersView.get` on `get_admin_org` → 403 `not_admin` for non-admins.
- [ ] **Task 3 — auth/me as the admin source (AC: #3)**
  - [ ] `AuthMeView` returns `is_admin` (`get_admin_org(request) is not None`); `api/auth.ts` `CurrentUser` gains `is_admin`. `AuthProvider.refresh` sets `isAdmin = me.is_admin` (drop the `getMembers` probe). `KeysPage` uses `useAuth().isAdmin` (no `getMembers`); `MembersPage` uses `useAuth().isAdmin`.
- [ ] **Task 4 — Tests (AC: #4)** — see ACs.

## Dev Notes

### Root cause

`ProtectedRoute` only checks authentication, `/members` + `/organization` used it, and `MembersView.get` served the roster to any member (`get_request_org`) with an `is_admin` flag. So authorization lived entirely in the nav (hidden links) — a non-admin could open `/members` by URL and even hit the API.

### Why auth/me carries is_admin now

Previously `AuthProvider` derived `isAdmin` by calling the members endpoint and reading its `is_admin` flag. Once that endpoint is admin-only (403 for non-admins), probing it is a fragile "403 = not admin" signal that also fires a 403 on every non-admin load. Putting `is_admin` on `auth/me` makes it the single, cheap source of truth for nav, route, and affordance gating.

### References

- `frontend/src/components/AdminRoute.tsx`, `frontend/src/App.tsx`, `frontend/src/auth/AuthProvider.tsx`, `frontend/src/api/auth.ts`, `frontend/src/pages/{MembersPage,KeysPage}.tsx`
- `backend/generate_sbom/users/views.py` (`MembersView.get`, `AuthMeView`)
- Related: `2-3-org-administration-and-membership-management.md`, `2-11-org-maintenance-navigation-for-admins.md`, `2-16-fix-make-admin-and-protect-global-admin.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
