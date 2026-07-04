# Story 10.2: Redirect to Login and Back

Status: review

## Story

As a user,
I want protected pages to send me to login and then back,
so that I return to where I was headed after signing in.

## Acceptance Criteria

1. Given I am not authenticated, when I open a protected route (`/upload`, `/history`, `/results/:taskId`, etc.), then I am redirected to `/login` with the **intended destination preserved** (router location state or a `?next=` param) (FR-N3).
2. Given I then log in successfully, when login completes, then I am redirected to the **originally requested page** — not a fixed default (FR-N4).
3. Given I navigate to `/login` directly (no intended destination), when I log in, then I land on a sensible default (e.g. `/dashboard` or `/upload`).
4. Given the redirect preserves state, when implemented, then `ProtectedRoute` captures the current `location` on redirect and `LoginPage` reads it on success; the round-trip is covered by a test.
5. Given I am already authenticated, when I visit `/login`, then I am sent to the default authenticated page rather than re-shown the form (recommended).

## Tasks / Subtasks

- [ ] Task 1 — Preserve intended destination (AC: #1)
  - [ ] In `ProtectedRoute`, redirect anonymous users with `<Navigate to="/login" state={{ from: location }} replace />` (capture via `useLocation`) — or a `?next=` param
- [ ] Task 2 — Return-to after login (AC: #2, #3)
  - [ ] In `LoginPage`, read `location.state.from` (or `?next=`) and `navigate(target, { replace: true })` on success; fall back to the default when absent
- [ ] Task 3 — Already-authed guard (AC: #5)
  - [ ] If already authenticated, `/login` redirects to the default authenticated page
- [ ] Task 4 — Tests (AC: #4)
  - [ ] Unauthenticated hit on a protected route → `/login` carrying the origin; logging in returns there; direct `/login` → default; round-trip covered
  - [ ] `pixi run ci` exits 0

## Dev Notes

`ProtectedRoute` currently does `<Navigate to="/login" replace />` with **no origin captured** — that's the gap. Add `state={{ from: location }}` (via `useLocation`) and have `LoginPage` consume it. `LoginPage` currently redirects to a fixed default on success; make that default the fallback only. Prefer router **location state** (cleaner, no URL clutter); `?next=` is an acceptable alternative if a shareable/bookmarkable login URL is wanted.

Builds on Story 10.1's shared auth state (use it for the already-authed guard and to know when login succeeded). If 10.1 introduces the auth context, `ProtectedRoute`/`LoginPage` should use it here rather than re-checking.

### References

- [Source: frontend/src/components/ProtectedRoute.tsx, pages/LoginPage.tsx, App.tsx]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.2]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- **ProtectedRoute** now captures the current `useLocation()` and redirects anonymous users with `<Navigate to="/login" state={{ from: location }} replace />` (router state, not a query param) — preserving pathname/search/hash.
- **LoginPage** reads `location.state.from` and, on successful login, calls the shared `refresh()` (from 10.1) then `navigate(target, { replace: true })` — returning to the intended page; falls back to `/dashboard` when there is no origin. An already-authenticated visit to `/login` short-circuits with `<Navigate>` (to the origin if present, else the default) instead of showing the form.
- **Tests:** ProtectedRoute carries `from` on redirect; LoginPage round-trip (returns to `/upload`), default fallback, already-authed guard, and failed-login stays on the form. The LoginPage test avoids `beforeEach(mockReset)` on the login mock (vitest false unhandled-rejection footgun).
- Gate: `pixi run ci` exits 0 — backend 262, frontend 90 (18 files).

### File List

- frontend/src/components/ProtectedRoute.tsx (capture `from`) + ProtectedRoute.test.tsx
- frontend/src/pages/LoginPage.tsx (return-to + already-authed guard) + LoginPage.test.tsx (new)
