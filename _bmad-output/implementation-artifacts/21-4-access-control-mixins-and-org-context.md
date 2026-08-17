# Story 21.4: Access-Control Mixins and Active-Org Context

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.3**. Every page story from 21.5 onward gates on these mixins and reads
> the active org from this context processor. **The highest-security story in Epic 21** — it replaces four
> client-side route guards with server-side enforcement.

## Story

As a security-conscious developer,
I want route protection and active-org resolution enforced server-side,
so that access decisions stop depending on client-side route guards that a user can bypass by editing
JavaScript.

## Acceptance Criteria

1. **Four route guards become server-side mixins.**
   Given `ProtectedRoute.tsx`, `OrgRoute.tsx`, `AdminRoute.tsx`, and `GlobalAdminRoute.tsx` gate pages in the
   browser, when they are replaced, then `LoginRequiredMixin` plus custom `UserPassesTestMixin` subclasses
   (org-member, org-admin, global-admin) enforce the same rules server-side, an **unauthenticated** request
   **redirects to login preserving the intended destination**, and an **authenticated-but-wrong-role** request
   returns **403** rather than a redirect.
2. **Active-org context replaces `AuthProvider`.**
   Given `AuthProvider.tsx` supplies `activeOrg`, `isAdmin`, and `isGlobalAdmin` to every component, when the
   equivalent is built, then a context processor exposes the same three values to every template, sourced from
   the existing `get_request_org` helper so the session-based active-org resolution is **shared with** — not
   duplicated from — the API path.
3. **The org switcher becomes a POST form.**
   Given `OrgSwitcher.tsx` posts to `/orgs/switch/`, when it is reimplemented, then the switcher is a
   CSRF-protected POST form in the app shell calling the existing org-switch service **directly** (AD-1: not
   over HTTP), it is **hidden when the user belongs to only one org** (Story 2.19), and switching updates the
   session's active org and re-renders the current page against it.
4. **Zero-org users get the same state everywhere.**
   Given `NoOrgState.tsx` renders for a user with no org memberships, and Story 2.18 restricts zero-org users
   to the home page, when the equivalent is built, then every org-scoped page renders the same "no
   organisation" state instead of an error, and a zero-org user cannot reach an org-scoped page by URL.
5. **Cross-org access leaks nothing.**
   Given org isolation is an invariant (**AD-2**), when a member of org A requests a resource belonging to org
   B, then the response is identical to the response for a non-existent resource — no distinction between
   "forbidden" and "not found" — for every org-scoped view.
6. **Authorisation is tested exhaustively.**
   Given access control is the highest-risk conversion in the epic, when the story completes, then unit tests
   assert every mixin against all four principal types (anonymous, member, org admin, global admin) **including
   cross-org denial**, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — Mixins (AC: #1)** — `LoginRequiredMixin` usage plus `OrgMemberRequiredMixin`,
  `OrgAdminRequiredMixin`, `GlobalAdminRequiredMixin`. Redirect for anonymous, 403 for wrong role.
- [ ] **Task 2 — Context processor (AC: #2)** — Expose `active_org`, `is_admin`, `is_global_admin`, reusing
  `generate_sbom.users.auth.get_request_org` (post-collapse: `inventory.users.auth`).
- [ ] **Task 3 — Org switcher form (AC: #3)** — POST form in `base.html`, calls the org-switch service
  directly; hidden when `len(orgs) <= 1`.
- [ ] **Task 4 — Zero-org state (AC: #4)** — Shared template partial; enforce at the mixin layer, not per page.
- [ ] **Task 5 — Cross-org indistinguishability (AC: #5)** — Ensure the org-scoped lookup raises 404-equivalent
  for both wrong-org and missing, matching the API's existing behaviour.
- [ ] **Task 6 — Authorisation test matrix (AC: #6)** — Four principals × each mixin, plus cross-org.

## Dev Notes

### Grounded facts (verified)

- Route guards: `frontend/src/components/{ProtectedRoute,OrgRoute,AdminRoute,GlobalAdminRoute}.tsx`, applied in
  `App.tsx` — `/organization` and `/members` are `AdminRoute`; `/keys`, `/upload`, `/results/:taskId`,
  `/history` are `OrgRoute`; `/platform/global-admins` is `GlobalAdminRoute`.
- `frontend/src/api/auth.ts` — `CurrentUser` carries `is_admin` (admin of the **active** org, Story 2.17) and
  `is_global_admin` (Story 2.12); both are described there as "the SPA's single source of truth for gating
  admin-only nav, routes, and actions".
- Backend helper: `generate_sbom.users.auth.get_request_org` handles **both** the session path and the API-key
  path (`base.py:49-50` comment). Reuse it — do not write a second resolver.
- Existing endpoints the new views' services back onto: `/orgs/switch/`, `/orgs/me/`, `/orgs/`, `/auth/me/`
  (`users/urls.py`).
- Related prior stories: 2.17 (admin-only pages enforced at route **and** API), 2.18 (zero-org users
  restricted to home), 2.19 (hide switcher for a single org), 13.1 (global admin tier).

### Why 403 rather than redirect for wrong-role

A redirect for an authenticated user who simply lacks the role turns an authorisation failure into a
navigation event, which hides the failure from tests and from logs. Anonymous → redirect (they can fix it by
logging in); authenticated-but-unauthorised → 403 (they cannot).

### Cross-org denial must not leak existence

`AD-2` and the SPA's own comment (`useJobStatus.ts`: "Cross-org and unknown jobs both surface as 403/404 — no
existence leak") establish the rule. The server-rendered path must preserve it: a wrong-org request and a
non-existent-object request must be indistinguishable to the client.

### Watch for

- **Do not duplicate `get_request_org`.** A second resolver that drifts from the API's is exactly the class of
  bug this story exists to prevent.
- **The switcher is a POST, never a GET link** — switching org is a state change and must carry CSRF.
- **`is_admin` is per-active-org**, not global. A user can be admin of org A and a plain member of org B;
  switching org changes `is_admin`. Test that transition explicitly.

### Testing standards

- A parametrised test matrix: {anonymous, member, org-admin, global-admin} × {each mixin} × {own org, other
  org}, asserting status codes and that no response body differs between wrong-org and missing.
- A test asserting the switcher is absent from the rendered shell for a single-org user.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.4: Access-Control Mixins and Active-Org Context]
- `frontend/src/components/{ProtectedRoute,OrgRoute,AdminRoute,GlobalAdminRoute,OrgSwitcher,NoOrgState}.tsx`,
  `frontend/src/auth/AuthProvider.tsx`, `frontend/src/App.tsx`, `generate_sbom/users/auth.py`,
  `generate_sbom/users/authentication.py`.
- Upstream: `21-3-server-rendered-ui-foundation.md`. Downstream: every page story 21.5–21.18.
- Architecture: AD-1 (no inter-app HTTP), AD-2 (org isolation), AD-14 (org/admin/auth model).

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
