# Story 10.3: Auto-Redirect to Login After Registration

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a newly registered user,
I want to be taken to the login page automatically after I register,
so that I don't have to find and click a login link to continue.

## Acceptance Criteria

1. **Auto-redirect.** After a successful registration, a brief confirmation is shown and the app **automatically navigates to `/login` after ~5 seconds** without requiring a manual click.
2. **Told what's happening + manual escape.** The success state tells the user what will happen (e.g. "Registration successful — redirecting to login…") and keeps a manual login link so an impatient user can go immediately.
3. **Timer cleanup.** If the user leaves the page before the timer fires (clicks the login link or navigates away), the pending timer is cleared — no navigation or state update after unmount (no stray redirect, no memory-leak warning).
4. **Tested.** Covered by a test using fake timers: the redirect fires after the delay and is cancelled on unmount.

## Tasks / Subtasks

- [ ] **Task 1 — Rewrite the registration success state (AC: #1, #2)**
  - [ ] In `frontend/src/pages/RegisterPage.tsx`, replace the current success `Alert` (which reads `result.org.slug` and shows "Your personal org is …") with a confirmation that does **not** reference an org, plus "redirecting to login…" text and a manual `Link`/`Button` to `/login`.
  - [ ] Track a "registered" success flag rather than `orgSlug` (see the 2.6 interaction below — `register()` no longer returns an org to display).
- [ ] **Task 2 — Redirect timer with cleanup (AC: #1, #3)**
  - [ ] On successful registration, start a ~5s timer (`setTimeout`) that calls react-router `useNavigate()('/login')`. Store the timer id and clear it in a `useEffect` cleanup (or clear on unmount) so it can't fire after the component unmounts.
  - [ ] Use `react-router`'s `useNavigate` (the app already uses react-router; `/register` and `/login` are public routes in `App.tsx`).
- [ ] **Task 3 — Test (AC: #4)**
  - [ ] Add `frontend/src/pages/RegisterPage.test.tsx` (Vitest + RTL, `vi.mock('../api/auth')`, `vi.useFakeTimers()`): after a mocked successful `register`, advancing ~5s navigates to `/login`; unmounting before the timer clears it (no navigation). Assert the manual link is present.

## Dev Notes

### Current state + the Story 2.6 interaction (important)

`RegisterPage.tsx` (read in full) today:
```tsx
const result = await register(email, password)
setOrgSlug(result.org.slug)      // line 21
...
<Alert severity="success">Account created. Your personal org is “{orgSlug}”.</Alert>   // line 33
```
Story 2.6 makes registration return **zero orgs** (`org: null`), so `result.org.slug` will be null/undefined and the "personal org" wording is wrong. This story rewrites that exact success block, so **remove the personal-org reference** and stop dereferencing `result.org`. Do not reintroduce an org display. (This also means: at the 2.6 foundation merge, RegisterPage must not crash on a null org even before 10.3 lands — 10.3 is the permanent fix.)

- Success detection: key off the successful `register()` resolving (a boolean flag), not off an org slug.
- `register()` client lives in `frontend/src/api/auth.ts`; `/register` and `/login` are public routes (not under `ProtectedRoute`) in `frontend/src/App.tsx`.

### Testing standards

- Vitest + React Testing Library, `*.test.tsx` co-located, **no MSW** — mock `../api/auth` with `vi.mock`. Use `vi.useFakeTimers()` / `vi.advanceTimersByTime(5000)` and wrap the component in a router (`MemoryRouter`) so `useNavigate` works; assert on the resulting location or a `Navigate` spy.

### Project Structure Notes

- Frontend-only: `frontend/src/pages/RegisterPage.tsx` (+ its new test). No backend or route-path changes.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.3: Auto-Redirect to Login After Registration]
- Current page: `frontend/src/pages/RegisterPage.tsx:21`, `:33`
- Interacting story: `_bmad-output/implementation-artifacts/2-6-zero-org-users-and-identity-decoupling.md` (register returns `org: null`)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
