# Story 10.7: Remove the Redundant /dashboard Page; Land Login on the Index Page

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a single, useful home after login instead of an empty placeholder,
so that I'm not dropped on a redundant page that duplicates the shell's controls.

## Acceptance Criteria

1. **`/dashboard` removed.** `DashboardPage.tsx` (+ its test) and the `/dashboard` route in `App.tsx` are deleted; no references to `DashboardPage` or `/dashboard` remain (`tsc`/grep clean).
2. **Login lands on the index page.** `LoginPage`'s `DEFAULT_AFTER_LOGIN` is `'/'`; a preserved `from` destination (Story 10.2 `ProtectedRoute` redirect) still wins — only the fallback changes.
3. **Tests + CI green.** The login round-trip test and the default-fallback test pass against `/`; `pixi run ci` is green.

## Tasks / Subtasks

- [ ] **Task 1 — Remove the page + route (AC: #1)**
  - [ ] Delete `frontend/src/pages/DashboardPage.tsx` and `frontend/src/pages/DashboardPage.test.tsx`.
  - [ ] `frontend/src/App.tsx`: remove the `DashboardPage` import and the `/dashboard` `<Route>`.
- [ ] **Task 2 — Repoint the login default (AC: #2)**
  - [ ] `frontend/src/pages/LoginPage.tsx`: `DEFAULT_AFTER_LOGIN = '/'` (keep `const target = from ?? DEFAULT_AFTER_LOGIN`).
- [ ] **Task 3 — Update tests / references (AC: #1, #3)**
  - [ ] `frontend/src/pages/LoginPage.test.tsx`: the default-fallback and already-authenticated tests used a `/dashboard` stub route — point them at `/` (rendering an "index page" stub) and update the assertions. `login-flow.test.tsx` only uses the `from`→`/upload` path, so it is unaffected.

## Dev Notes

- `/dashboard` (`DashboardPage`) is a scaffolding stub: not in `SideNav`, it duplicates the shell's org switcher + logout and shows an empty "Your SBOM jobs will appear here." The real jobs dashboard is `HistoryPage` (`/history`, Stories 6.1–6.3), which already handles the zero-org `NoOrgState`. So `/dashboard` is pure redundancy.
- The index page (`/`, `HomePage`) is being enriched into a real landing page separately (Story 12.8); landing login there is intentional.
- Both `DashboardPage` and `HistoryPage` render `NoOrgState` for zero-org users, so removing the former loses no zero-org handling.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.7]
- `frontend/src/App.tsx` (`/dashboard` route), `frontend/src/pages/LoginPage.tsx:13` (`DEFAULT_AFTER_LOGIN`), `frontend/src/pages/DashboardPage.tsx` (removed), `frontend/src/pages/HistoryPage.tsx` (the real jobs dashboard)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
