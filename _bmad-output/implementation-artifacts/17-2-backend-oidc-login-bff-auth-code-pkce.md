# Story 17.2: Backend OIDC Login (BFF, Authorization Code + PKCE)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Second story of Epic 17 — build after 17.1.** The security core of Phase 1: the Django backend acts as a
> **Backend-for-Frontend (BFF)** and performs the OIDC **Authorization Code + PKCE** flow server-side, then
> establishes the ordinary **Django session** — the SPA stays cookie-based, no tokens in the browser. Depends
> on Story 17.1 (config/discovery/flag). Story 17.3 (JIT provisioning) plugs into this story's callback;
> Story 17.4 (logout) mirrors its session handling; Story 17.5 (frontend) drives it.

> **⚠ SECURITY-CRITICAL story.** PKCE, `state`, `nonce`, and full `id_token` validation are acceptance
> criteria, not nice-to-haves. See "Security acceptance criteria" below.

> **Implemented with django-allauth (Story 17.1's proposed dep), not hand-rolled.** allauth's generic OIDC
> provider (`allauth.socialaccount.providers.openid_connect`) already performs the **Authorization Code flow
> with PKCE + `state` + `nonce`** server-side and hands off to Django's session. The security ACs below are
> therefore satisfied by **leveraging + verifying allauth's flow** (correct config, session/BFF hand-off), not
> by re-implementing PKCE/state/nonce. Do not add the dependency until the user approves (Story 17.1 GATE).

## Story

As a user of an OIDC-enabled installation,
I want to log in through my organization's IdP and come back to the app already signed in,
so that I authenticate once against the IdP and the app trusts that login — without the browser ever holding a
token.

## Acceptance Criteria

1. **Initiate (authorize redirect) — via allauth.**
   Given `OIDC_ENABLED=true`, when the SPA triggers login (the initiate route — allauth's provider login URL,
   optionally wrapped as `GET /api/v1/auth/oidc/login/`), then allauth generates the **PKCE**
   `code_verifier`/`code_challenge` (S256), a random `state`, and a `nonce`, stashes them **server-side** (in
   the session), and redirects the browser to the IdP **authorization endpoint** (from discovery, Story 17.1)
   with `response_type=code`, `client_id`, `redirect_uri`, `scope`, `state`, `nonce`, and `code_challenge`. The
   AC is that allauth is configured so this holds (PKCE enabled) — verified, not re-implemented.
2. **Callback (code → token exchange) — via allauth.**
   Given the IdP redirects back to the callback (allauth's provider callback, mapped to `OIDC_REDIRECT_URI`)
   with `code` + `state`, when allauth handles it, then it (a) verifies `state` matches the stashed value
   (**CSRF/replay defense**; mismatch → reject), and (b) exchanges the `code` at the IdP **token endpoint**
   using the stored `code_verifier` (PKCE), over the back channel with the client secret.
3. **`id_token` validation — via allauth.**
   Given the token response, when the `id_token` is validated, then **all** of: signature (against the IdP
   **JWKS** from discovery), `iss` == configured issuer, `aud` == `OIDC_CLIENT_ID`, `exp`/`iat`/`nbf` within
   skew, and `nonce` == the stashed nonce, must pass (allauth's OIDC provider performs this). Any failure
   rejects the login (logged via structlog; no session established).
4. **Establish the Django session (BFF).**
   Given a validated `id_token`, when login completes, then the user is resolved via allauth's adapter (Story
   17.3 provisioning/linking) and Django `login()` sets the **session cookie** — the same session mechanism the
   local `LoginView` uses today (`users/views.py:257`). **No access/refresh/id token is returned to the
   browser**; the SPA continues to authenticate by session cookie (`credentials: 'include'`).
5. **CSRF cookie continuity.**
   Given the SPA sends `X-CSRFToken` on writes (`client.ts:64-66,88-90`), when the OIDC session is
   established, then the `csrftoken` cookie is issued just as the local login does
   (`@ensure_csrf_cookie`, `users/views.py:228`), so post-login writes work identically.
6. **Tokens stay server-side.**
   Given the OIDC tokens, when the flow finishes, then any retained access/refresh token lives **only**
   server-side (session/DB), never in a response body or a non-HttpOnly cookie — the browser holds only the
   Django session (+ csrf) cookie, preserving the current security posture.
7. **Errors are explicit.**
   Given a `state` mismatch, a token-exchange error, or an `id_token` validation failure, when it occurs, then
   the user is redirected to a login-error state and the failure is logged with a specific exception type
   (never a bare `except`, never silently swallowed — CLAUDE.md §2).
8. **Flag-gated + coexisting.**
   Given `OIDC_ENABLED=false`, when the OIDC endpoints are hit, then they are inactive (404/flag-guarded) and
   local password login (`LoginView`) is unaffected either way (coexistence, Story 17.8).
9. **Tested; CI green.**
   Backend tests cover PKCE params on the authorize redirect, `state` verification (match → proceed, mismatch
   → reject), a mocked token exchange, `id_token` validation (happy path + each failing claim: bad `iss`,
   bad `aud`, expired, bad `nonce`), session established on success, and no token in any response body.
   `pixi run ci` green.

## Security acceptance criteria (restated, must all hold — provided by allauth, verified here)

- **PKCE (S256)** on every authorization request; `code_verifier` never leaves the server.
- **`state`** generated, stashed server-side, verified on callback — CSRF/replay defense.
- **`nonce`** generated, stashed, and checked against the `id_token` claim — replay defense.
- **Full `id_token` validation**: signature (JWKS), `iss`, `aud`, `exp`/`iat`/`nbf` (+ skew), `nonce`.
- **BFF/session**: tokens never reach the browser; only the Django session + csrf cookies do.
- **CSRF**: the SPA's existing `X-CSRFToken` on writes continues to protect session-authenticated mutations.

These are delivered by **django-allauth**'s generic OIDC provider out of the box — the story's job is to
**configure it correctly** (PKCE on, issuer/audience set) and **verify** these properties by test, not to
hand-roll the flow.

## Tasks / Subtasks

- [ ] **Task 1 — Initiate (AC: #1)** — wire allauth's OIDC provider login (optionally behind
  `GET /api/v1/auth/oidc/login/`) so PKCE + `state` + `nonce` are generated + session-stashed; flag-guarded.
- [ ] **Task 2 — Callback (AC: #2, #3, #4, #5)** — use allauth's callback: `state` verify, `code` exchange
  (PKCE), `id_token` validation (JWKS/iss/aud/exp/nonce); resolve user via the adapter (delegates to Story
  17.3); `login()` + csrf cookie. Reconcile allauth's callback URL/redirect with our session/active-org model.
- [ ] **Task 3 — Server-side token custody (AC: #6)** — ensure any allauth-retained tokens stay server-side
  only; nothing token-bearing in a response body.
- [ ] **Task 4 — Error handling (AC: #7, #8)** — specific exceptions, structlog, redirect-to-error; flag guard.
- [ ] **Task 5 — Tests (AC: #9)** — see ACs; mock the IdP token/JWKS endpoints (no live network); assert
  allauth is configured with PKCE on and the security properties hold.
- [ ] `pixi run ci` green.

## Dev Notes

### Fixed decisions (product owner)

- **BFF / server-side session via django-allauth.** allauth's generic OIDC provider runs the Authorization
  Code + PKCE flow server-side and sets the **Django session cookie**. The SPA stays cookie-based
  (`credentials: 'include'`) — **no tokens in the browser**. This is the load-bearing architectural decision
  for Phase 1, and allauth's native session/server-side model is exactly why it was chosen.
- **Reuse the existing session mechanics.** OIDC login funnels into the same `login()` + `ensure_csrf_cookie`
  session the local `LoginView` already uses — the session, csrf, and downstream authorization are identical
  whether the user came in via password or OIDC. (allauth's `SocialAccount`/`EmailAddress` models + URL/adapter
  conventions must be reconciled with our custom `User`/`LoginView`/active-org session — see the Story 17.1
  integration caveat.)
- **Leverage, don't hand-roll.** PKCE/state/nonce/full-id_token-validation are provided by allauth; the ACs are
  satisfied by correct configuration + verification, not a bespoke flow. A misconfiguration that disables any
  of them is a defect.

### Current state (verified)

- Local login precedent: `users/views.py::LoginView` (`:229`) uses `authenticate()` (`:249`) + `login()`
  (`:257`); `@method_decorator(ensure_csrf_cookie, ...)` (`:228`) sets `csrftoken`. `LogoutView` (`:269`)
  calls `logout()` (`:275`).
- SPA session/cookie posture: `frontend/src/api/client.ts` sends `credentials: 'include'` (`:72,95`) and
  `X-CSRFToken` from the `csrftoken` cookie (`:64-66,88-90`).
- Config/discovery/flag: from Story 17.1 (`OIDC_ENABLED`, issuer, client, discovery endpoints, JWKS).

### Testing standards

- Backend: pytest + DRF `APIClient`; **intercept the IdP** (mock/`respx`/library test hooks) — never hit a
  live IdP. Assert redirect query params, session-stashed values, `login()` side effect, and no token in the
  response body.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.2: Backend OIDC Login (BFF, Authorization Code + PKCE)]
- `backend/generate_sbom/users/views.py:228-283` (`LoginView`/`LogoutView` session precedent),
  `frontend/src/api/client.ts:64-95` (cookie/csrf posture)
- Related: `17-1-oidc-provider-configuration-and-discovery.md`
- Downstream: `17-3-jit-user-provisioning-and-account-linking.md`, `17-4-oidc-logout-and-session-lifecycle.md`,
  `17-5-frontend-sso-login.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
