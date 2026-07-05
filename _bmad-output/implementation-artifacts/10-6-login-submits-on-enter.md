# Story 10.6: Login Form Submits on Enter (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user on the login screen,
I want to press Enter in a field to submit the form,
so that I can log in with the keyboard instead of having to click the button.

## Acceptance Criteria

1. **Reproduce first (failing test).** A test is written **before** any code change that simulates
   pressing **Enter** in the email (or password) field of the login form and asserts the form submits
   — `login` is called (and/or `handleSubmit` runs). This test must **fail** against the current code,
   reproducing the reported bug.
2. **Fix implicit submission.** The root cause is identified and fixed so implicit form submission
   works with the MUI `Paper component="form"` structure (`LoginPage.tsx:49-77`): confirm the rendered
   element is a real `<form>` and that Enter in a text field triggers its `onSubmit`. The change stays
   minimal.
3. **No regression to click-submit.** The existing click-to-submit path (the `<Button type="submit">`,
   `LoginPage.tsx:74-76`) still works.
4. **Tested.** Pressing **Enter** in a login field submits the form (the reproduction test now passes),
   and click-to-submit remains covered.

## Tasks / Subtasks

- [ ] **Task 1 — Reproduce the bug with a failing test (AC: #1)**
  - [ ] `frontend/src/pages/LoginPage.test.tsx`: render `LoginPage` (mock `useAuth` `status: 'anon'`,
    `MemoryRouter`, mock `login` from `../api/auth`). Type into Email + Password, then simulate Enter,
    e.g. `await userEvent.type(screen.getByLabelText('Password'), '{Enter}')`, and assert `login` was
    called with the entered credentials (`handleSubmit` ran). Confirm this **fails** first.
- [ ] **Task 2 — Diagnose and fix (AC: #2, #3)**
  - [ ] Verify what the form actually renders: MUI `Paper component="form"` should emit a real `<form>`
    so `onSubmit` fires on Enter. Investigate whether it does — check that `component="form"` reaches
    the DOM, that `onSubmit={handleSubmit}` is bound to the `<form>` (not swallowed), and that
    `handleSubmit` calls `event.preventDefault()` (it does, `LoginPage.tsx:33`). Likely fixes if it is
    broken: ensure the `<Button type="submit">` sits inside the rendered `<form>`, or make the form a
    plain `<Box component="form">` / native `<form>` wrapper if `Paper` interferes with `onSubmit`.
    Apply the **minimal** change that makes Enter submit.
  - [ ] Do not change the auth logic in `handleSubmit` (`LoginPage.tsx:32-42`) beyond what's needed;
    keep `preventDefault`, `login`, `refresh`, and the redirect intact.
- [ ] **Task 3 — Confirm both paths (AC: #3, #4)**
  - [ ] Keep/extend a click-to-submit test (click "Log in" → `login` called) alongside the Enter test.

## Dev Notes

### Why this story exists (the bug)

Pressing **Enter** in the login fields does not submit — the user must click "Log in". `LoginPage.tsx`
*looks* correct: `<Paper component="form" onSubmit={handleSubmit}>` (`LoginPage.tsx:49-53`) wrapping the
Email/Password `TextField`s with a `<Button type="submit">` (`LoginPage.tsx:74-76`), which normally
gives implicit submission. Because the structure appears right, the fix is **test-first**: reproduce
before changing code, then fix whatever the reproduction reveals.

### Diagnostic notes

- Implicit submission requires a **native `<form>`** in the DOM with a submit control inside it. Verify
  MUI's `Paper component="form"` actually renders `<form onSubmit=…>` (it should — `component` sets the
  root element) and that nothing intercepts the submit event.
- `handleSubmit` already calls `event.preventDefault()` (`LoginPage.tsx:33`), so a working submit won't
  reload the page.
- If the reproduction shows Enter *does* work under jsdom but not in the browser, capture that in the
  Dev Agent Record and widen the test (e.g. assert on the rendered element type / `role="form"`), then
  address the real-DOM difference.

### Current shipped state (verified)

- `LoginPage.tsx:49-77`: `Paper component="form" variant="outlined" onSubmit={handleSubmit}` → Email
  `TextField` (with `autoFocus`, Story 10.4) → Password `TextField` → `Button type="submit"`.
- `handleSubmit` (`LoginPage.tsx:32-42`): `preventDefault` → `login(email, password)` → `refresh()` →
  `navigate(target, { replace: true })`; error path sets an alert.

### Testing standards

- Vitest + RTL + `@testing-library/user-event`. Mock `../auth/AuthProvider` (`useAuth` `status:'anon'`,
  `refresh`) and `../api/auth` (`login`). Wrap in `MemoryRouter`. Use `getByLabelText('Email')` /
  `'Password'`; trigger Enter with `userEvent.type(field, '{Enter}')` or `fireEvent.submit`. No MSW.

### Project Structure Notes

- Frontend-only, single-file fix: `frontend/src/pages/LoginPage.tsx` (+ `LoginPage.test.tsx`). No
  backend, no route change. Independent of Stories 2.12 / 10.5 (no shared files).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.6: Login Form Submits on Enter (Bugfix)]
- Login page: `frontend/src/pages/LoginPage.tsx:49` (form), `:32` (`handleSubmit`), `:74` (submit button)
- Related story: `10-4-autofocus-email-on-login.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
