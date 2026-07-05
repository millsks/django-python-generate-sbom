# Story 10.5: Account Menu Shows the Logged-In User, Not the Org (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a signed-in user,
I want the account/profile menu to show my own identity,
so that I can confirm which account I'm logged in as instead of seeing the org name where my name
should be.

## Acceptance Criteria

1. **Provider exposes the current user.** `AuthProvider` **stores** the `getMe()` result and
   **exposes** the current `user` (`{id, email}`) via `useAuth` — a new `user` field on `AuthValue`
   — instead of discarding it (`AuthProvider.tsx:37`).
2. **Account menu shows the user's email.** The account menu in `Layout` shows the logged-in
   **user's email** (`user.email`) as the primary identity, replacing the current `activeOrg.name`
   display (`Layout.tsx:115-119`). The active org may remain as a **secondary** context line, but the
   user identity is what the menu leads with.
3. **Works for zero-org users.** A signed-in user with **zero** orgs still sees their email in the
   account menu (identity does not depend on having an active org, Story 2.6) — the menu no longer
   collapses to nothing when `activeOrg` is null.
4. **Tested.** A test asserts the account menu shows the logged-in user's email.

## Tasks / Subtasks

- [ ] **Task 1 — Capture + expose the user in `AuthProvider` (AC: #1)**
  - [ ] `frontend/src/auth/AuthProvider.tsx`: `refresh()` calls `await getMe()` and discards it
    (`AuthProvider.tsx:37`). Capture it (`const me = await getMe()`), add a `user` state, and set it.
  - [ ] Add `user: CurrentUser | null` to the `AuthValue` interface (`AuthProvider.tsx:13-19`), the
    memoized `value` (`AuthProvider.tsx:76-79`), and reset it to `null` in the `catch` (anon) and
    `logout` paths (`AuthProvider.tsx:39-42, 62-70`). Import `CurrentUser` from `../api/auth`
    (already exported there, `auth.ts:10`).
  - [ ] **Coordinate with Story 2.12**, which also captures this `getMe()` result (for
    `is_global_admin`) on the same line and extends the same `AuthValue`. Implement together so one
    `const me = await getMe()` feeds both `user` and `isGlobalAdmin`.
- [ ] **Task 2 — Show the user's email in the account menu (AC: #2, #3)**
  - [ ] `frontend/src/components/Layout.tsx`: destructure `user` from `useAuth()` (`Layout.tsx:56`).
    In the `Menu` (`Layout.tsx:114-129`), replace the `activeOrg && <MenuItem>{activeOrg.name}</MenuItem>`
    header (`:115-119`) with the user's email as the primary identity. Optionally keep `activeOrg.name`
    as a secondary line beneath it. Keep the existing `Divider` + `Logout` item.
  - [ ] Ensure the identity line renders when `user` is set even if `activeOrg` is null (AC #3) — don't
    gate the whole header on `activeOrg`.
- [ ] **Task 3 — Test (AC: #4)**
  - [ ] `frontend/src/components/Layout.test.tsx`: extend the `useAuth` mock's `authState` helper to
    include a `user: { id, email }`, render `Layout`, open the account menu (click the "Account menu"
    `IconButton`, `Layout.tsx:111`), and assert the user's email is shown. Add a zero-org case
    (`activeOrg: null`) asserting the email still renders.

## Dev Notes

### Why this story exists (the bug)

The account menu shows the **org** name where the user's identity should be. Verified root cause:
`Layout.tsx:115-119` renders `activeOrg.name` inside the account `Menu`, and `AuthProvider.refresh()`
calls `getMe()` (`AuthProvider.tsx:37`) only to establish auth — it **discards** the returned user, so
`AuthValue` never exposes it and the menu has nothing else to show. For a zero-org user the
`activeOrg && …` block collapses, so no identity appears at all.

### Current shipped state (verified)

- `AuthProvider.AuthValue` = `{ status, activeOrg, isAdmin, refresh, logout }` — no `user`
  (`AuthProvider.tsx:13-19`).
- `await getMe()` result discarded at `AuthProvider.tsx:37`.
- Account menu header: `{activeOrg && <MenuItem disabled>…{activeOrg.name}…</MenuItem>}`
  (`Layout.tsx:115-121`).
- `getMe()` already returns `CurrentUser` = `{ id, email }` (`frontend/src/api/auth.ts:10-20`) — no
  backend change needed for this story (the email is already in the payload).

### Cross-story coordination (10.5 ↔ 2.12)

Both stories extend `AuthProvider` and consume the `getMe()` call at `AuthProvider.tsx:37`:
- **10.5** adds `user` to `AuthValue` (from `getMe()`).
- **2.12** adds `isGlobalAdmin` to `AuthValue` (and `is_global_admin` to the `auth/me` payload +
  `CurrentUser`).
Land them together (or one then rebase the other) so a single `const me = await getMe()` feeds both
fields and the `AuthValue` interface grows once. This story does **not** itself change the backend
`auth/me` response (email is already present); 2.12 is the one that adds `is_global_admin` server-side.

### Testing standards

- Vitest + RTL. Mock `../auth/AuthProvider` `useAuth` with an `authState({ ... , user })` helper (the
  existing `Layout.test.tsx` already mocks `useAuth`). Wrap in `MemoryRouter`. Open the menu via the
  "Account menu" button's `aria-label`. No MSW.

### Project Structure Notes

- Frontend-only: `frontend/src/auth/AuthProvider.tsx`, `frontend/src/components/Layout.tsx`
  (+ `Layout.test.tsx`). No backend change, no route change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.5: Account Menu Shows the Logged-In User, Not the Org (Bugfix)]
- Provider: `frontend/src/auth/AuthProvider.tsx:13,37,76`; API: `frontend/src/api/auth.ts:10,18`
- Menu: `frontend/src/components/Layout.tsx:56,111,114-121`
- Related stories: `10-1-app-shell-and-auth-aware-navigation.md`,
  `2-6-zero-org-users-and-identity-decoupling.md`, `2-12-restrict-org-creation-to-global-admins.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
