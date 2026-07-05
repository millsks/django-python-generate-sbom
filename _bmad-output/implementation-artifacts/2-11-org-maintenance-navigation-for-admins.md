# Story 2.11: Org Maintenance Navigation for Admins

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an org admin (or a global admin),
I want a clear "Organization" control center in the side navigation,
so that I have one obvious place to manage members, API keys, and org settings
instead of hunting for scattered admin links.

## Acceptance Criteria

1. **Admin-only nav entry.** The side navigation shows an **"Organization"** (org
   maintenance) entry that is visible **only** when the logged-in user is an admin
   of the active org **or** a global admin — i.e. gated on `isAdmin` from `useAuth`.
   A non-admin never sees it.
2. **Control center for org administration.** The entry leads to a clear place to
   administer the org: members (add-existing / create-new / remove / make-admin),
   API keys, create org, and org info. Build it consistently with the existing
   admin-gated nav (the Members link is already admin-gated, Story 10.1/12.3) —
   **either** a new consolidated "Organization" page/route that links to (or embeds)
   the existing Members and API Keys management, **or** an admin-gated nav group that
   collects those destinations. Reuse the existing `MembersPage` and `KeysPage`
   rather than reimplementing their logic.
3. **Consistent with the shell.** The entry renders in `SideNav` using the existing
   `NavIcon` vocabulary and active-route styling; on mobile it closes the temporary
   drawer via the existing `onNavigate` callback like the other items.
4. **Tested.** Tests assert the Organization entry is present for an admin
   (`isAdmin: true`) and absent for a non-admin (`isAdmin: false`); if a new route is
   added, it is admin-reachable and wired in `App.tsx`.

## Tasks / Subtasks

- [ ] **Task 1 — Decide the shape (AC: #2)**
  - [ ] Pick one, consistent with the current shell: **(A)** a new consolidated
    `/organization` route + `OrganizationPage` that presents members + API keys + create-org
    + org info as sections (reusing `MembersPage`/`KeysPage` content), with a single
    "Organization" `SideNav` entry; **or** **(B)** an admin-gated nav **group** in `SideNav`
    that lists the existing destinations (Members, API Keys, and a create-org affordance)
    under an "Organization" heading. Prefer (A) if a control-center page is wanted; (B) is
    lighter. Record the choice in the Dev Agent Record.
- [ ] **Task 2 — SideNav entry, admin-gated (AC: #1, #3)**
  - [ ] `frontend/src/components/SideNav.tsx`: the nav already appends the admin-only Members
    item via the `isAdmin` ternary (`SideNav.tsx:41`). Add the "Organization" entry (or group)
    the same way — admin-only, using a `NavIcon` (e.g. a settings/business icon; add one to
    `frontend/src/icons.ts` `NavIcon` if needed, `icons.ts:37`). Keep the `component={NavLink}` +
    `&.active` styling and the `onNavigate` mobile-close behavior (`SideNav.tsx:48-69`).
  - [ ] `isAdmin` already flows from `useAuth` through `Layout` into `SideNav` (`Layout.tsx:56,145,156`;
    `AuthProvider.tsx` computes `isAdmin`) — no new plumbing needed.
- [ ] **Task 3 — Route + page (only if choosing shape A) (AC: #2, #4)**
  - [ ] Add `frontend/src/pages/OrganizationPage.tsx` and a `<Route path="/organization" …>` wrapped
    in `ProtectedRoute` in `frontend/src/App.tsx` (mirror the `/members` and `/keys` routes,
    `App.tsx:32-47`). Gate content on `isAdmin`/`activeOrg` and reuse the existing management UI;
    show `NoOrgState` when there is no active org (as `MembersPage`/`KeysPage` do).
- [ ] **Task 4 — Tests (AC: #4)**
  - [ ] `frontend/src/components/SideNav.test.tsx` (new) or extend `Layout.test.tsx`: render with
    `isAdmin: true` → the "Organization" entry is present; with `isAdmin: false` → absent. Follow
    `Layout.test.tsx`'s `useAuth` mock + `authState({ isAdmin })` pattern.
  - [ ] If shape A: a test that the `/organization` route renders for an admin.

## Dev Notes

### Why this story exists (the gap)

The side nav has no dedicated place for org administration — admin actions (members,
keys, create-org) are reachable only via individual links, and there is no obvious
"control center." This story adds an admin-gated "Organization" entry that consolidates
org administration, matching the existing pattern where the **Members** link is already
admin-gated in the nav.

### Current nav gating pattern (reuse it)

`SideNav` receives `isAdmin` and appends the admin-only Members item:
```tsx
const items = isAdmin ? [...NAV_ITEMS, { to: '/members', label: 'Members', Icon: NavIcon.members }] : NAV_ITEMS
```
(`SideNav.tsx:41`). Extend this same `isAdmin` gate for the "Organization" entry/group — do
not invent a separate permission path. `isAdmin` is the single source of truth from
`AuthProvider` (true for org admins and global admins alike, since global admins hold real
ADMIN memberships — Story 2.8).

### Reuse existing management UI

`MembersPage` (`frontend/src/pages/MembersPage.tsx`) and `KeysPage`
(`frontend/src/pages/KeysPage.tsx`) already implement member and key management with
`NoOrgState`/`PageState` handling and their own `isAdmin` fetch. A consolidated Organization
page should compose/link these, not duplicate their logic. Create-org already exists via
`CreateOrgDialog` / `createOrg()` (`api/orgs.ts:33`) and the org switcher (Story 2.5).

### Cross-story dependencies

- **Story 10.1 / 12.3** — the auth-aware shell + `SideNav` this builds on (admin-gated Members
  link is the precedent).
- **Story 2.10** — the Members page gains "create new user" alongside "add existing"; the
  Organization control center should surface both.
- **Story 2.5 / 2.4** — create-org and API-key management surfaced from the control center.

### Testing standards

- Vitest + RTL, mock `useAuth` with `vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))`
  and an `authState({ isAdmin })` helper (see `frontend/src/components/Layout.test.tsx`). Wrap in
  `MemoryRouter` for `NavLink`. No MSW.

### Project Structure Notes

- Frontend-only: `frontend/src/components/SideNav.tsx`, `frontend/src/icons.ts` (if a new icon),
  and — for shape A — `frontend/src/pages/OrganizationPage.tsx` + a route in `frontend/src/App.tsx`.
- No backend change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.11: Org Maintenance Navigation for Admins]
- Nav: `frontend/src/components/SideNav.tsx:41`, `frontend/src/components/Layout.tsx:56,145,156`
- Auth: `frontend/src/auth/AuthProvider.tsx` (`useAuth`/`isAdmin`)
- Routes: `frontend/src/App.tsx:32-47`; pages `frontend/src/pages/MembersPage.tsx`, `KeysPage.tsx`
- Related stories: `10-1-app-shell-and-auth-aware-navigation.md`, `12-3-application-layout-header-footer-side-navigation.md`, `2-10-admin-create-new-user-account.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
