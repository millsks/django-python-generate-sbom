---
baseline_commit: 7c83282
---

# Story 21.5: Authentication Pages

Status: review

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

- [x] **Task 1 — `LoginForm` + view (AC: #1, #3, #4, #6)** — Crispy-rendered; calls the existing login service;
  honours `?next=`; autofocus on email.
- [x] **Task 2 — `RegistrationForm` + view (AC: #1, #2, #6)** — Password validators from
  `AUTH_PASSWORD_VALIDATORS` (`base.py:116-119`) surface as inline field errors; duplicate email is a field
  error, not a 500.
- [x] **Task 3 — Logout (AC: #5)** — POST-only, CSRF-protected, session flushed.
- [x] **Task 4 — Account menu (AC: #5)** — Email + logout in the shell header from 21.3.
- [x] **Task 5 — Tests + gate (AC: #7)**.

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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **499 passed**, coverage **96.14%**; frontend **223 passed**.
- `mypy src` clean over 90 files; `ruff check .` clean.
- **25 new tests** in `tests/unit/test_auth_pages.py`.
- Route resolution: `ui-login` → `/login`, `ui-register` → `/register`, `ui-logout` → `/logout`;
  the API's `login`/`register` still → `/api/v1/auth/{login,register}/` (untouched).
- Live server check — `/login` and `/register` served by **Django**; `/logout` GET → **405**;
  `/`, `/upload`, `/history` still served by the **SPA**.
- Real browser-equivalent round trip with `curl` and a cookie jar: fetched `/login`, captured
  the 64-char CSRF token, POSTed credentials → **302 to `/`**, session persisted, and `/ui/`
  then rendered `admin@example.com` in the account menu.
- Login failure parity: wrong password and unknown email produce **identical** response bodies
  once the CSRF token and the echoed email are masked.

### Completion Notes List

**A cross-story regression this story caused, found by the gate.** Adding the POST logout form
to `base.html` means the shell now emits a CSRF token — and Django re-salts that token on every
render. Story 21.4's `test_cross_org_and_missing_objects_are_indistinguishable` compared two
404 bodies byte-for-byte, so it started failing on the token alone. The security property is
unchanged (a rotating token distinguishes nothing); the test had been relying on the incidental
absence of any CSRF token in the shell. Now masks the token before comparing. Worth noting
because the same latent assumption could bite any test that byte-compares two rendered pages.

**Two django-stubs/runtime mismatches, resolved without weakening the checks.**
1. `FormView[LoginForm]` type-checks but **raises `TypeError` at import** — django-stubs
   declares the class generic while Django's runtime class is not subscriptable. It broke all
   25 tests at once with "type 'FormView' is not subscriptable". Reverted to the unsubscripted
   base with a narrow `# type: ignore[type-arg]` and a comment naming the cause. The documented
   alternative (`django_stubs_ext.monkeypatch()`) was rejected: it would make production
   settings import a type-stubs helper.
2. `validate_password(..., user)` and `auth_login(request, user)` are typed against the host's
   **concrete** User, which the app must not name. Both go through the existing
   `inventory.common.users.user_ref` seam rather than new ignores — the same mechanism Story
   21.2 established for exactly this mismatch.

**Real paths claimed, not a `/ui/` prefix.** `/login`, `/register`, and `/logout` are now
served by Django and added to the SPA catch-all's negative lookahead. This is what makes Story
21.4's `LOGIN_URL = "/login"` and the whole bounce-to-login round trip genuinely work — a
`/ui/login` mount would have left the mixins redirecting to a SPA page. The SPA's client-side
router still has `/login` and `/register` routes, so an in-app navigation stays on the SPA while
a fresh request for those URLs gets the Django page; that coexistence is intentional for the rest
of the epic and is documented in `config/urls.py`.

**Route names follow the `ui-` convention from 21.4.** The API already owns `login` and
`register` as route names, and a duplicate resolves to whichever registers last. Two tests assert
the *rendered* `href`/`action` points at the HTML route and explicitly **not** at
`/api/v1/auth/...`, which is the only way that class of bug is visible.

**Server-rendered views live in `pages.py`, not `views.py`.** Story 21.2 preserved the file-role
convention in which `views.py` means DRF views. A new `inventory/urls_pages.py` aggregates page
routes for Stories 21.5-21.18 and is mounted at the site root, separate from the per-submodule
DRF urlconfs mounted under `/api/v1/`.

**What genuinely got simpler, as the story predicted.** Enter-to-submit (Story 10.6) and
autofocus (Story 10.4) are a native form behaviour and one widget attribute. `{% csrf_token %}`
replaces the manual `X-CSRFToken` handling. And the four `AUTH_PASSWORD_VALIDATORS` — configured
since Story 1.3 but invisible to the SPA, which surfaced a weak password as a generic 400 banner
— now render inline against the password field. Four tests pin that: too short, entirely
numeric, too common, and too similar to the email.

**The similarity validator needed a probe instance.** `UserAttributeSimilarityValidator` silently
does nothing when `validate_password` is passed `user=None`, so the form builds an unsaved user
carrying the submitted email. `test_a_password_similar_to_the_email_is_rejected` pins it,
because a silently-skipped validator looks exactly like a passing one.

**Account-enumeration resistance is asserted on the whole page, not the message.** Wrong password
and unknown email are compared body-to-body (masking the CSRF token and the echoed email — the
submitter already knows the address they typed), so an extra hint, a differing count, or a
field-level marker on `email` would all fail the test. A message-only assertion would not catch
those.

**Duplicate-email registration is a deliberate disclosure.** It is a field error saying the email
is taken. Registration cannot avoid disclosing this — the alternative is silently not creating
the account — so it is stated plainly rather than obscured. This is a different threat model from
login, and the code says so.

**No SSO button**, per the story's explicit instruction: Epic 17 (OIDC) is entirely unimplemented.
`test_login_page_offers_no_sso_button` pins the absence so a later story cannot add a
non-functional button before Epic 17 lands.

**Session handling.** Login goes through `django.contrib.auth.login`, which cycles the session key
(session-fixation defence); logout uses `auth_logout`, which flushes the session entirely. Tests
assert `SESSION_KEY` is present after login and **absent** after logout, plus that a GET logout
(405) and a CSRF-less POST logout (403) both leave the session intact.

**Not done here.** No SSO. No password reset — outside this story's ACs and not present in the
SPA either. The nav still points at SPA paths for pages not yet converted (21.6 onward replace
them one at a time).

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (6)**
- `src/django_apps/inventory/users/forms.py` — `LoginForm`, `RegistrationForm`
- `src/django_apps/inventory/users/pages.py` — `LoginPageView`, `RegisterPageView`, `LogoutPageView`
- `src/django_apps/inventory/urls_pages.py` — the app's page urlconf (`ui-` names)
- `src/django_apps/inventory/templates/inventory/auth/login.html`, `register.html`
- `tests/unit/test_auth_pages.py` (25 tests)

**Modified (4)**
- `src/config/urls.py` — mount `inventory.urls_pages` at the root; free `login|register|logout`
  from the SPA catch-all
- `src/django_service/templates/base.html` — `Sign in` → `{% url 'ui-login' %}`; the 21.3
  placeholder logout **link** replaced by a CSRF-protected POST form
- `tests/unit/test_access_control.py` — mask the rotating CSRF token before comparing two
  error-page bodies (see the regression note)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Converted login, registration, and logout to server-rendered Django pages calling the existing services directly (AD-1). Claimed the real `/login`, `/register`, `/logout` paths from the SPA catch-all, which is what makes Story 21.4's bounce-to-login round trip work. Registration creates no org (Story 2.6) and flashes a message before redirecting to sign-in (Story 10.3). The four `AUTH_PASSWORD_VALIDATORS` now render inline against the password field. Failed login is indistinguishable between unknown email and wrong password, asserted body-to-body. Logout is a CSRF-protected POST that flushes the session. `pixi run ci` exit 0; 499 backend tests at 96.14%. |
