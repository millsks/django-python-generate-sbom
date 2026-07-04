# Story 10.1: App Shell & Auth-Aware Navigation

Status: review

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- **Shared auth state:** `src/auth/AuthProvider.tsx` — `useAuth()` → `{ status: 'loading'|'authed'|'anon', activeOrg, isAdmin, refresh, logout }`. On mount `getActiveOrg()` (success → authed + org; throw → anon), then `getMembers().is_admin` for `isAdmin`. `logout()` calls `api/auth.logout()` then clears. `refresh()` re-runs the check (for Story 10.2 after login).
- **ProtectedRoute** refactored to consume `useAuth()` (loading → null; anon → `<Navigate to="/login" replace/>`; authed → children). Return-to is Story 10.2.
- **App shell:** `src/components/Layout.tsx` — MUI AppBar with the title (→`/`), auth-aware nav (anon: Login/Register; authed: Upload/History/API Keys + `OrgSwitcher` + theme toggle + account menu → Logout), `Members` only when `isAdmin`, active-route highlight via `NavLink` `.active`. Renders `<Outlet/>`.
- **Theme toggle** moved into the app bar: `ThemeModeProvider` now exposes `useThemeMode()` + a `<ThemeToggle/>` (color=inherit) and no longer renders the fixed floating button.
- **App.tsx** nests all existing routes (paths + ProtectedRoute wrappers unchanged, incl. `*`→Home) under `<Route element={<Layout/>}>`, inside `<AuthProvider>`; `main.tsx` still wraps `App` in `ThemeModeProvider`.
- **Tests:** Layout (nav per auth state + admin, active route, logout, wraps route via Outlet — `ThemeToggle` stubbed for isolation), ProtectedRoute (authed/anon/loading), AuthProvider (authed+admin, anon, logout). No existing tests broke (pages are tested directly).
- Gate: `pixi run ci` exits 0 — backend 262, frontend 85 (17 files).

### File List

- frontend/src/auth/AuthProvider.tsx (new) + AuthProvider.test.tsx (new)
- frontend/src/components/Layout.tsx (new) + Layout.test.tsx (new)
- frontend/src/components/ProtectedRoute.tsx (use auth context) + ProtectedRoute.test.tsx (new)
- frontend/src/ThemeModeProvider.tsx (useThemeMode + ThemeToggle; removed floating button)
- frontend/src/App.tsx (Layout + AuthProvider nesting)

## Story

As a user,
I want persistent navigation in the UI,
so that I can move between pages by clicking instead of typing URLs.

## Acceptance Criteria

1. Given any page, when it renders, then a persistent top app bar (a shell layout wrapping the routes) shows the app name/home link and navigation for the current auth state, with the active route visually indicated (FR-N1).
2. Given I am logged out, when the nav renders, then it shows **Login** and **Register** and no protected links.
3. Given I am logged in, when the nav renders, then it shows the primary app links (Upload / New job, History, API Keys), the **org switcher** (`OrgSwitcher`), the **theme toggle** (`ThemeModeProvider`), and a user menu with **Logout**; **Members** (and any other admin-only links) appear only for org admins (FR-N2).
4. Given shared auth state is needed by both the nav and route protection, when implemented, then a single source of truth (auth context/provider or hook) exposes `authed` / current user / active org / `logout`, so the nav and `ProtectedRoute` don't each re-derive it.
5. Given Logout, when clicked, then the session ends (`api/auth.logout`) and I land on a public page (Home/Login) with the nav in the logged-out state.
6. Given the shell, when it wraps the routes, then `App.tsx` renders pages inside the layout (nav + router `<Outlet/>`), keeping the existing route paths unchanged.

## Tasks / Subtasks

- [ ] Task 1 — Shared auth state (AC: #4)
  - [ ] Add an auth context/provider (or hook) exposing `{ authed, user, activeOrg, isAdmin, logout, refresh }`, sourced from `api/orgs.getActiveOrg` (+ any user/membership endpoint); provide it above the router
  - [ ] Refactor `ProtectedRoute` to consume it (removing its own per-mount `getActiveOrg` check) — coordinate with Story 10.2
- [ ] Task 2 — App shell layout (AC: #1, #6)
  - [ ] Add a `Layout` (MUI `AppBar`/`Toolbar`) with the app title/home link and a nav region; render `<Outlet/>` for page content
  - [ ] Refactor `App.tsx` to nest the routes under the layout (paths unchanged)
- [ ] Task 3 — Auth/role-aware nav (AC: #2, #3, #5)
  - [ ] Logged-out: Login, Register. Logged-in: Upload, History, API Keys; org switcher; theme toggle; user menu → Logout; Members only when `isAdmin`
  - [ ] Active-route highlight (react-router `NavLink`/`useLocation`)
  - [ ] Logout calls `api/auth.logout`, clears auth state, navigates to a public page
- [ ] Task 4 — Tests
  - [ ] Nav shows the right items per auth state and admin role; active-route indicated; Logout ends session + updates nav; layout wraps routes
  - [ ] `pixi run ci` exits 0

## Dev Notes

Current state: `App.tsx` renders pages directly (no shell). `ProtectedRoute` checks auth via `getActiveOrg()` per mount. `OrgSwitcher` (Story 2.2) and `ThemeModeProvider` (Story 5.7) already exist to drop into the bar. `api/auth.ts` has `login`/`logout`/`register`; `api/orgs.ts` has `getActiveOrg`. Determine admin role from the active-org/membership data (whatever the org API returns). Keep it frontend-only.

Coordinates with Story 10.2 (the redirect-to-login-and-back), which also touches `ProtectedRoute` + `LoginPage` — sequence 10.1's auth-context introduction with 10.2's redirect logic to avoid churn.

### References

- [Source: frontend/src/App.tsx, components/ProtectedRoute.tsx, components/OrgSwitcher.tsx, ThemeModeProvider.tsx, api/auth.ts, api/orgs.ts]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.1]

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
