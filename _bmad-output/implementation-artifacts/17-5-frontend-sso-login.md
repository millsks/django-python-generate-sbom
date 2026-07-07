# Story 17.5: Frontend SSO Login

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Frontend story of Epic 17 — build after 17.2 (needs the initiate endpoint) and ideally after 17.3/17.4.**
> Adds the "Sign in with SSO" affordance to the login page, shown **only when `OIDC_ENABLED`** (read from
> `/api/v1/config/`, Story 17.1), handles the redirect hand-off to the backend BFF flow, and coexists with the
> local login form under the flag. Post-login identity still flows through `auth/me` (unchanged).

## Story

As a user on an OIDC-enabled installation,
I want a "Sign in with SSO" button on the login page,
so that I can start the IdP login without leaving the familiar login screen, while local password login still
works when it's enabled.

## Acceptance Criteria

1. **Flag-gated affordance.**
   Given the login page, when it loads, then it reads `oidc_enabled` from `getAppConfig()`
   (`frontend/src/api/config.ts`, Story 17.1) and renders a **"Sign in with SSO"** control **only when
   `oidc_enabled === true`**; when false, the page is exactly as today (local form only).
2. **Redirect hand-off (no tokens in the browser).**
   Given SSO is available, when the user clicks "Sign in with SSO", then the browser navigates to the backend
   **initiate** endpoint (`/api/v1/auth/oidc/login/`, or the allauth provider login URL it wraps, Story 17.2) —
   a full-page navigation/redirect, **not** a `fetch` — so the backend BFF (django-allauth) drives the
   Authorization Code + PKCE flow and the IdP round-trip. The SPA never handles an authorization code or any
   token (BFF decision).
3. **Coexistence under the flag.**
   Given both auth methods enabled, when the login page renders, then the local email/password form **and** the
   SSO button are both shown (local form primary, SSO as an alternative), consistent with the visual system
   (Epic 12). When `oidc_enabled` is false, only the local form shows; a future cutover (Story 17.8) may hide
   the local form.
4. **Post-login routing via `auth/me`.**
   Given the backend established the session (Story 17.2) and redirected back to the SPA, when the app loads,
   then identity is resolved through `AuthProvider`'s `auth/me` call exactly as for local login — a zero-org
   user (Story 17.3) lands on Home (Story 2.18); an org user lands on their normal post-login route. **No
   OIDC-specific client identity handling** — `auth/me` remains the single source of truth.
5. **Error surface.**
   Given the backend redirects back with a login-error state (Story 17.2 AC #7), when the SPA lands, then the
   login page shows a clear, generic error message (no token/claim details leaked) and lets the user retry.
6. **Tested; CI green.**
   Frontend tests (Vitest + RTL) cover: SSO button shown when `oidc_enabled` true and hidden when false; the
   button triggers a navigation to the initiate URL (not a `fetch`); local form still renders/works under the
   flag; the login-error state renders. `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Read the flag (AC: #1)** — `LoginPage` consumes `getAppConfig().oidc_enabled` (cache/reuse if
  already fetched app-wide) to decide whether to render the SSO control.
- [ ] **Task 2 — SSO control + redirect (AC: #2, #3)** — a "Sign in with SSO" button doing a full-page
  navigation to `/api/v1/auth/oidc/login/`; lay it out alongside the local form per Epic 12 styling.
- [ ] **Task 3 — Error handling (AC: #5)** — render the backend login-error state generically.
- [ ] **Task 4 — Tests (AC: #6)** — see ACs; mock `getAppConfig`, assert render + navigation, not token logic.
- [ ] `pixi run ci` green (frontend).

## Dev Notes

### Fixed decisions (product owner)

- **BFF hand-off, not a client OAuth flow.** The SSO button is a **redirect to the backend**, which owns the
  entire OIDC flow. The SPA never touches a code or token — it stays cookie/session-based
  (`credentials: 'include'`). This is the whole point of the BFF decision.
- **Flag-gated + coexisting.** SSO shows only when `OIDC_ENABLED`; local login coexists under the flag until a
  later cutover (Story 17.8).
- **`auth/me` stays the identity source.** Post-login routing is unchanged — no OIDC-specific identity code in
  the SPA.

### Current state (verified)

- Login UI: `frontend/src/pages/LoginPage.tsx` (+ `LoginPage.test.tsx`, `login-flow.test.tsx`); submits via
  `api/auth.ts::login` today.
- Identity: `frontend/src/auth/AuthProvider.tsx` drives identity from `auth/me` (`api/auth.ts::getMe`,
  `CurrentUser`); zero-org → Home (Story 2.18).
- Flag channel: `frontend/src/api/config.ts::getAppConfig()` → `AppConfig` (gains `oidc_enabled` in
  Story 17.1); client posture `frontend/src/api/client.ts` (`credentials: 'include'`, `X-CSRFToken`).

### Testing standards

- Vitest + RTL; mock `getAppConfig` for both flag states; assert the SSO control's presence/absence and that
  clicking it navigates to the initiate URL (spy on `window.location`/navigation), not a `fetch`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.5: Frontend SSO Login]
- `frontend/src/pages/LoginPage.tsx`, `frontend/src/auth/AuthProvider.tsx`, `frontend/src/api/config.ts`,
  `frontend/src/api/auth.ts`, `frontend/src/api/client.ts`
- Related: `17-1-oidc-provider-configuration-and-discovery.md`,
  `17-2-backend-oidc-login-bff-auth-code-pkce.md`, `10-4-autofocus-email-on-login.md`,
  `12-8-landing-page-front-page.md`
- Downstream: `17-8-coexistence-flag-rollout-and-cutover.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
