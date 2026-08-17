# Story 21.5: Authentication Pages

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.4**. Uses the base template (21.3) and the redirect-to-login behaviour
> of the mixins (21.4). **No SSO button** — Epic 17 (OIDC) is entirely `ready-for-dev` and unimplemented.

## Story

As a user,
I want to register, log in, and log out through server-rendered pages,
so that I can access the application without a JavaScript framework.

## Acceptance Criteria

1. **Login and registration become Django forms.**
   Given `LoginPage.tsx` and `RegisterPage.tsx` post JSON to `/auth/login/` and `/auth/register/`, when they
   are converted, then Django `Form` classes rendered through crispy replace them, calling the existing auth
   services **directly** (AD-1, AD-3 — not over HTTP), and validation errors render **inline against the
   offending field** rather than as a single banner.
2. **Registration creates no org.**
   Given Story 2.6 made registration create no organisation (`auth.ts`: "Registration creates no org — always
   null today"), when a user registers, then no org is created and the user becomes a zero-org user who sees
   the Story 21.4 zero-org state.
3. **Post-registration and post-login navigation is preserved.**
   Given registration redirects to login on success (Story 10.3) and login lands on the originally requested
   page or the index (Story 10.2, `DEFAULT_AFTER_LOGIN = '/'`), when the pages are converted, then both
   behaviours are preserved, and the intended-destination round trip works for a user who was bounced from a
   protected page by the Story 21.4 mixins.
4. **Form ergonomics are preserved.**
   Given login autofocuses the email field (Story 10.4) and submits on Enter (Story 10.6), when the page is
   converted, then the email field is autofocused on load and Enter submits the form.
5. **The account menu and logout work.**
   Given Story 10.5 shows the logged-in user in an account menu, when the shell renders for an authenticated
   user, then the account menu shows their email and a **CSRF-protected POST** logout that ends the session and
   redirects to the index.
6. **Failure modes are explicit.**
   Given bad credentials and duplicate-email registration are the two common failures, when either occurs,
   then the form re-renders with a specific message, the password field is cleared, and **no** distinction is
   made between "unknown email" and "wrong password".
7. **Gate green.**
   When the story completes, then tests cover successful and failed login, duplicate-email registration, the
   redirect-to-intended-destination path, autofocus, and logout session invalidation, and `pixi run ci`
   exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — `LoginForm` + view (AC: #1, #3, #4, #6)** — Crispy-rendered; calls the existing login service;
  honours `?next=`; autofocus on email.
- [ ] **Task 2 — `RegistrationForm` + view (AC: #1, #2, #6)** — Password validators from
  `AUTH_PASSWORD_VALIDATORS` (`base.py:116-119`) surface as inline field errors; duplicate email is a field
  error, not a 500.
- [ ] **Task 3 — Logout (AC: #5)** — POST-only, CSRF-protected, session flushed.
- [ ] **Task 4 — Account menu (AC: #5)** — Email + logout in the shell header from 21.3.
- [ ] **Task 5 — Tests + gate (AC: #7)**.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/pages/LoginPage.tsx` — `DEFAULT_AFTER_LOGIN = '/'`; uses `useLocation()` state to return to the
  intended destination (Story 10.2).
- `frontend/src/api/auth.ts` — `register(email, password)` → `{ user, org }` where `org` is **always null**
  (Story 2.6); `login(email, password)` → `{ org }`; `logout()` POST; `getMe()` → `CurrentUser`.
- `backend/generate_sbom/users/urls.py` — `auth/register/`, `auth/login/`, `auth/logout/`, `auth/me/`.
- `backend/config/settings/base.py:116-119` — four `AUTH_PASSWORD_VALIDATORS` already configured; the Django
  form will surface them automatically, which the SPA had to do by hand.
- Session auth is already the web path (`base.py:53`), so `django.contrib.auth.login()`/`logout()` semantics
  apply unchanged.
- Prior stories in scope: 10.2 (redirect to login and back), 10.3 (auto-redirect to login after registration),
  10.4 (autofocus email), 10.5 (account menu shows logged-in user), 10.6 (login submits on Enter).

### What gets simpler

Django forms surface `AUTH_PASSWORD_VALIDATORS` as per-field errors for free, and `{% csrf_token %}` replaces
the manual `X-CSRFToken` header handling in `frontend/src/api/client.ts`. Enter-to-submit is native form
behaviour — Story 10.6 exists only because the SPA had to implement it.

### Watch for

- **Do not add an SSO button.** Story 17.5 (`frontend-sso-login`) is `ready-for-dev`, not done, and the whole
  OIDC epic is unimplemented. Adding a non-functional button is worse than omitting it.
- **Do not leak account existence** — a wrong password and an unknown email must produce the same message.
- **Session fixation**: use Django's `login()` so the session key cycles.

### Testing standards

- Tests for: valid login, invalid password, unknown email (same response as invalid password), duplicate-email
  registration, weak-password rejection, `?next=` round trip, logout invalidating the session.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.5: Authentication Pages]
- `frontend/src/pages/{LoginPage,RegisterPage,login-flow}.tsx`, `frontend/src/api/auth.ts`,
  `generate_sbom/users/{views,services,serializers}.py`.
- Upstream: `21-4-access-control-mixins-and-org-context.md`.

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
