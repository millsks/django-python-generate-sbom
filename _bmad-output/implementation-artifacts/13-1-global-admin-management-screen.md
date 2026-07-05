# Story 13.1: Global-Admin Management Screen

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Depends on Stories 2.12 (`is_global_admin` on `auth/me` + `AuthProvider`), 2.8 (`grant_global_admin`), and 2.17 (admin-route + API-authorization pattern).** Implement AFTER 2.16/2.17 merge so it reuses the route-guard pattern rather than reinventing it.

## Story

As a global admin,
I want a screen to see, grant, and revoke global admins,
so that I can manage the platform's superuser tier without shell or DB access.

## Acceptance Criteria

1. **Global-admin-only access.** A new route + nav entry for the screen is shown only when `isGlobalAdmin`, and is enforced at BOTH the route (non-global-admins redirected) and the API (403) — not by nav hiding alone.
2. **List.** The screen lists current global admins (the ADMIN-org members) by email.
3. **Grant by email.** Granting global admin by a **registered** email adds them via `grant_global_admin` (ADMIN org + admin of every org). Unknown email → clear error, no auto-create.
4. **Revoke = remove + demote everywhere.** Revoking a global admin **removes them from the ADMIN org AND demotes their role to `member` in every non-admin org** (decided semantics). Confirmed with a dialog (destructive).
5. **Last-global-admin guard.** Revoking the last global admin is blocked (the ADMIN org must never lose its last member — Story 2.9). A global admin may revoke themselves only if not the last.
6. **Tested; CI green.** Backend + frontend tests per the Tasks; `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Backend: list + revoke services/endpoints (AC: #2, #3, #4, #5)**
  - [ ] `services.py`: add `list_global_admins() -> QuerySet[User]` (ADMIN-org members) and `revoke_global_admin(user)`: guard against removing the last global admin (raise a new `LastGlobalAdminError(MembershipError)`); delete the user's ADMIN-org `OrgMembership`; then `OrgMembership.objects.filter(org__is_admin_org=False, user=user, role=ADMIN).update(role=MEMBER)`.
  - [ ] Extend grant to accept an **email** (look up the registered user; `NoSuchUserError` if none) so the UI can grant by email — either extend `GrantGlobalAdminView` or add an email path. `grant_global_admin` itself is unchanged.
  - [ ] Views/urls: `GET /api/v1/admin/global-admins/` (list) and `DELETE /api/v1/admin/global-admins/<user_id>/` (revoke), both gated on `is_global_admin` (reuse the `_NOT_GLOBAL_ADMIN` 403 envelope from `GrantGlobalAdminView`, `views.py:~136`). Revoke returns 204.
- [ ] **Task 2 — Frontend: the screen (AC: #1, #2, #3, #4)**
  - [ ] New page (e.g. `frontend/src/pages/GlobalAdminsPage.tsx`) at a route like `/platform/global-admins`, wrapped in a **global-admin-only** guard (build on Story 2.17's `AdminRoute` — a `GlobalAdminRoute` or a `requireGlobalAdmin` variant gated on `useAuth().isGlobalAdmin`).
  - [ ] Nav: a global-admin-only entry (shown only when `isGlobalAdmin`) — e.g. a "Global Admins" / "Platform" item in `SideNav`.
  - [ ] `api/` client: `listGlobalAdmins()`, `grantGlobalAdmin(email)`, `revokeGlobalAdmin(userId)`. UI: list (email + revoke button w/ confirm dialog), grant-by-email input, distinct errors (no-such-user, last-global-admin).
- [ ] **Task 3 — Tests (AC: #6)**
  - [ ] Backend: list returns ADMIN-org members; grant-by-email (success + no-such-user); revoke removes ADMIN membership AND demotes to member in all non-admin orgs; last-global-admin revoke blocked; all endpoints 403 for non-global-admins.
  - [ ] Frontend (Vitest + RTL, no MSW): route redirects a non-global-admin; list/grant/revoke render and call the API; revoke confirms first.

## Dev Notes

### Current state (verified)

- `is_global_admin` / `grant_global_admin` / `get_the_admin_org` — `backend/generate_sbom/users/services.py`. Global admin = ADMIN-org (`Org.is_admin_org=True`) membership; grant back-fills admin of every org.
- Only a bare grant endpoint exists: `GrantGlobalAdminView` (`POST /api/v1/admin/global-admins/`, `{user_id}`, global-admin-gated). No list, no revoke.
- `isGlobalAdmin` reaches the frontend via `auth/me` + `AuthProvider` (Story 2.12).

### Design decisions (product owner)

- **Revoke = remove from ADMIN org + demote to `member` in every non-admin org.** We do not track which admin roles predated global-admin, so all drop to member; a per-org admin can re-promote as needed (per-org promote is Story 2.16). This is intentional over "remove from ADMIN org only."
- Per-org admin (Stories 2.3/2.7/2.16) is a separate concern and must NOT be conflated — this screen only manages the global (ADMIN-org) tier.

### Testing standards

- Backend: pytest `@pytest.mark.django_db`, DRF `APIClient`, reuse ADMIN-org / global-admin fixtures (Story 2.8/2.12 tests). Frontend: Vitest + RTL, mock the api module with `vi.mock`, wrap in `MemoryRouter`.

### Project Structure Notes

- Backend: `users/{services,views,urls}.py` + tests. Frontend: new page + a global-admin route guard + `SideNav` entry + api client + tests. No model/migration change (all derived from ADMIN-org membership).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 13.1: Global-Admin Management Screen]
- `backend/generate_sbom/users/services.py` (`is_global_admin`, `grant_global_admin`, `get_the_admin_org`), `views.py` (`GrantGlobalAdminView`, `_NOT_GLOBAL_ADMIN`)
- Related: `2-8-global-admin-org-and-cross-org-provisioning.md`, `2-12-restrict-org-creation-to-global-admins.md`, `2-17-admin-route-and-api-authorization.md`, `2-9-membership-edge-cases.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
