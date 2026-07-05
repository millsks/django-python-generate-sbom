# Story 10.4: Autofocus the Email Field on the Login Page

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user arriving at the login page (often auto-redirected from registration),
I want the email field to be focused automatically,
so that I can start typing my credentials immediately without clicking into the field.

## Acceptance Criteria

1. **Autofocus on mount.** When the login page renders, the **email** input receives
   focus automatically, so a user redirected from registration (Story 10.3) can type
   right away.
2. **Only when the form is shown.** Focus is applied only when the login form is
   actually rendered (i.e. not when an already-authenticated visitor is redirected
   away via the existing `<Navigate>` short-circuit) and does not steal focus on a
   re-render mid-typing.
3. **Tested.** A test asserts the email input is the focused element after the login
   page renders.

## Tasks / Subtasks

- [ ] **Task 1 — Autofocus the email field (AC: #1, #2)**
  - [ ] In `frontend/src/pages/LoginPage.tsx`, focus the email `TextField` on mount. Prefer MUI's
    declarative `autoFocus` prop on the email `TextField` (`LoginPage.tsx:56-62`) — it focuses on
    first render and won't re-steal focus. (If a ref-based approach is used instead, a
    `useEffect(() => ref.current?.focus(), [])` with `inputRef` is the alternative; `autoFocus` is
    simpler and preferred.)
  - [ ] The `status === 'authed'` early `<Navigate>` (`LoginPage.tsx:28-30`) already prevents the form
    from rendering for a signed-in user, so `autoFocus` naturally applies only to the real form (AC #2).
    Do not add focus logic above that guard.
- [ ] **Task 2 — Test (AC: #3)**
  - [ ] Add/extend `frontend/src/pages/LoginPage.test.tsx` (Vitest + RTL): render the login page (mock
    `useAuth` as `status: 'anon'`, wrap in `MemoryRouter`) and assert the email input has focus, e.g.
    `expect(screen.getByLabelText('Email')).toHaveFocus()`.

## Dev Notes

### Why this story exists (the gap)

Story 10.3 auto-redirects a freshly registered user to `/login` after ~5s. On arrival the
email field is not focused, so the user must click into it before typing. Autofocusing the
email input closes that small friction so the redirect lands the user ready to type.

### Current state

`LoginPage.tsx` (read in full) renders an email `TextField` then a password `TextField`
inside a `Paper` form (`LoginPage.tsx:56-69`). An already-authenticated visitor is redirected
before the form renders via `if (status === 'authed') return <Navigate to={target} replace />`
(`LoginPage.tsx:28-30`), so autofocus only ever applies to the anonymous login form. `autoFocus`
on the email field is the minimal change.

### Register → login relationship

`RegisterPage.tsx` (Story 10.3) navigates to `/login` ~5s after a successful registration
(`RegisterPage.tsx:23-27`). This story does not change `RegisterPage`; it only makes the
destination (the login form) focus its email field on arrival.

### Testing standards

- Vitest + React Testing Library, `frontend/src/pages/LoginPage.test.tsx`, mock `../auth/AuthProvider`
  (`useAuth`) with `status: 'anon'`, wrap in `MemoryRouter`, no MSW. Use `@testing-library/jest-dom`'s
  `toHaveFocus()` (already available in the frontend test setup) and `getByLabelText('Email')`.

### Project Structure Notes

- Frontend-only, single-file change: `frontend/src/pages/LoginPage.tsx` (+ its test). No backend,
  no route change. `RegisterPage.tsx` is referenced for context only — do not modify it.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.4: Autofocus the Email Field on the Login Page]
- Login page: `frontend/src/pages/LoginPage.tsx:56` (email field), `:28` (authed short-circuit)
- Register page (context): `frontend/src/pages/RegisterPage.tsx:23`
- Related story: `10-3-auto-redirect-to-login-after-registration.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
