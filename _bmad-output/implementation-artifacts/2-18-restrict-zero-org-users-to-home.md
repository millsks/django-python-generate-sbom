# Story 2.18: Restrict Zero-Org Users to the Home Page; the ADMIN Org Is Never a Working Org (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a signed-in user with no organization (and as a global admin),
I want to only be able to reach the home page and never have the system ADMIN org act as my workspace,
so that I can't upload or view history "in" an org I don't really work in.

## Acceptance Criteria

1. **The ADMIN org is never the active org — everywhere.** `get_request_org`'s **session path** validates the pinned `active_org_id` against a NON-admin membership (`memberships.filter(org_id=active_id, org__is_admin_org=False)`), mirroring the fallback path that already excludes it (Story 2.12). A user whose only membership is the ADMIN org (a global admin) resolves to **no active org** (zero-org) — the ADMIN org is never returned as the active working org for anyone, even a global admin, whether the id was pinned in the session or reached via fallback.
2. **Zero-org users are redirected to home at the route.** An authenticated user with no active org is REDIRECTED from every org-scoped route — `/upload`, `/history`, `/keys`, `/members`, `/organization`, `/results/*` — to `/` (home). The redirect is enforced at the route (a guard), not just by the per-page `NoOrgState`. Only home (and `/login`, `/register`, plus any global-admin-only screen) is reachable for a zero-org user. Anonymous users still go to `/login` (existing `ProtectedRoute`/`AdminRoute` behavior, preserving the destination).
3. **Home hides the upload CTA for zero-org users.** On the home page, a zero-org user sees NO "Upload a manifest" CTA and instead a clear "You're not in an organization yet — ask an admin to add you" state (reuse `NoOrgState`'s copy). A user WITH an active org still sees the normal landing page and the CTA.
4. **Backend denies with no active org (defense in depth).** Org-scoped endpoints continue to deny when there is no active org — the route guard is convenience, not the security boundary. Tests cover: ADMIN org never active via the session path (pinned ADMIN `active_org_id` → no active org) and via fallback (ADMIN-only member → no active org); zero-org redirect from an org-scoped route to `/`; the home CTA hidden for a zero-org user.

## Tasks / Subtasks

- [ ] **Task 1 — Exclude the ADMIN org on the session path (AC: #1, #4)**
  - [ ] `backend/generate_sbom/users/auth.py` `get_request_org`: change the session lookup at line 37 from `memberships.filter(org_id=active_id).first()` to `memberships.filter(org_id=active_id, org__is_admin_org=False).first()`, so a pinned ADMIN `active_org_id` no longer resolves. The fallback (line 44) already filters `org__is_admin_org=False`; keep it. Net effect: a user whose only membership is the ADMIN org gets `None` (zero-org).
- [ ] **Task 2 — Route guard for zero-org users (AC: #2)**
  - [ ] Introduce an org-scoped route guard (e.g. `OrgRoute`, alongside `ProtectedRoute`/`AdminRoute`) that: `loading` → nothing; `anon` → `/login` (preserving `from`); authed but `activeOrg == null` → `<Navigate to="/" replace />`; else render children. `AuthProvider` already exposes `activeOrg` (null when zero-org).
  - [ ] `frontend/src/App.tsx`: wrap the org-scoped routes (`/upload`, `/history`, `/keys`, `/results/:taskId`) with the new guard. `/members` and `/organization` already use `AdminRoute` — a zero-org user is not an admin of any active org (`isAdmin` false), so they already redirect to `/`; confirm and, if needed, compose so zero-org still lands on `/` rather than depending only on the admin flag.
- [ ] **Task 3 — Home page zero-org state (AC: #3)**
  - [ ] `frontend/src/pages/HomePage.tsx`: when the user is authed with no active org, hide the "Upload a manifest" CTA and render the `NoOrgState` empty-state copy ("ask an admin to add you"). Anonymous and org-having users see the existing landing page unchanged.
- [ ] **Task 4 — Tests (AC: #4)**
  - [ ] Backend (`backend/tests/`): a request with `active_org_id` pinned to the ADMIN org resolves to no active org (session path); a user whose only membership is the ADMIN org resolves to no active org (fallback path); an org-scoped endpoint denies with no active org.
  - [ ] Frontend: the new guard redirects a zero-org user (`activeOrg == null`) from an org-scoped route to `/`; `HomePage` hides the upload CTA and shows the no-org copy for a zero-org user, and shows the CTA when an active org exists.

## Dev Notes

### Root cause

- `backend/generate_sbom/users/auth.py` `get_request_org`: the fallback path already excludes the ADMIN org (`org__is_admin_org=False`, Story 2.12) so an unfiltered `first()` can't pin a global admin to it — but the **session path** (`memberships.filter(org_id=active_id).first()`, auth.py:37) does NOT exclude it. A pinned `active_org_id` pointing at the ADMIN org therefore still resolves it as the active working org, so a global admin (a member of the ADMIN org) can end up with "Admin" as their active org and upload/view history "in" it.
- `frontend/src/pages/HomePage.tsx`: the "Upload a manifest" CTA (`/upload`, HomePage.tsx:72) is unconditional.
- Org-scoped pages render `NoOrgState` but are still reachable by a zero-org user — no route-level redirect, only a per-page empty state.

### Operational aside (not this story's code)

The reporter is a **global admin** — a member of the system ADMIN org — which is why they saw the ADMIN org as a workspace and the "Create organization" affordance. The code fix here stops the ADMIN org from ever being a workspace (AC #1); it does NOT change who is a global admin. Removing a specific user from the global-admin tier is the **revoke** flow (Story 13.1) or a shell operation (`bootstrap_admin_org` / the platform-admin screen), not this story.

### Notes

- Depends on / overlaps **Story 13.1** (global-admin management screen) — 13.1 also touches routes and `AuthProvider`. Implement **after 13.1 merges** to avoid churn on `App.tsx` and the auth context.
- `NoOrgState` (`frontend/src/components/NoOrgState.tsx`) still offers a create-org affordance for global admins; reuse its copy for the home zero-org state. A global admin with zero active orgs still reaches home and can create an org there / from the switcher (Story 2.19), so restricting them to home is not a dead end.

### References

- `backend/generate_sbom/users/auth.py` (`get_request_org` session path, line 37)
- `backend/generate_sbom/users/selectors.py` (`get_user_orgs` — the already-correct ADMIN-org exclusion this mirrors)
- `frontend/src/App.tsx` (route wiring), `frontend/src/components/ProtectedRoute.tsx`, `frontend/src/components/AdminRoute.tsx` (guard pattern to follow)
- `frontend/src/pages/HomePage.tsx` (`/upload` CTA), `frontend/src/components/NoOrgState.tsx` (copy to reuse)
- `frontend/src/auth/AuthProvider.tsx` (`activeOrg` null == zero-org)
- Related: `2-6-zero-org-users-and-identity-decoupling.md`, `2-12-restrict-org-creation-to-global-admins.md`, `2-8-global-admin-org-and-cross-org-provisioning.md`, `13-1-global-admin-management-screen.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
