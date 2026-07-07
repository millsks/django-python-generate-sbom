# Story 17.1: OIDC Provider Configuration, Discovery & Feature Flag

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **First story of Epic 17 — build it first.** It establishes the installation-wide OIDC configuration
> (issuer, client id/secret, scopes, redirect), the `OIDC_ENABLED` feature flag, and OIDC **discovery**
> (`.well-known/openid-configuration`) that every later Epic 17 story reads. It also exposes the flag to the
> SPA by extending the existing `/api/v1/config/` endpoint (Story 11.20), which Story 17.5 (frontend SSO)
> reads to decide whether to render the "Sign in with SSO" affordance. **Full Epic 17 build order:
> 17.1 → 17.2 → 17.3 → 17.4 → 17.5, with 17.6 → 17.7 as a parallel resource-server track, and 17.8 last.**

> **⚠ NEW RUNTIME DEPENDENCY — GATE.** Phase 1 needs an OIDC Relying-Party library. The recommendation is
> **`django-allauth`** using its generic OIDC provider
> (`allauth.socialaccount.providers.openid_connect`) — it is **natively server-side / session-based**, matching
> our BFF decision exactly, and configures the issuer by **discovery** (IdP-agnostic). The **resource-server**
> half (Stories 17.6/17.7) uses **`authlib`** or **`PyJWT`** instead — allauth does **not** validate incoming
> OAuth2 bearer/JWT tokens on the API, so JWKS/JWT validation stays with authlib/PyJWT (see the division of
> labor in the epic intro). Per the project rule, **a new runtime dependency requires the user's explicit
> approval** — this story **proposes** `django-allauth` (+ `authlib`/`PyJWT` for the API side) and treats
> approval as a gate; do **not** add anything to `pixi.toml` / `backend/pyproject.toml` until the user approves.
> If approval is pending when 17.1 starts, the settings scaffolding (config keys + flag) can land first with the
> discovery/validation wiring stubbed behind the flag.

## Story

As an operator,
I want to configure a single external OpenID Provider (issuer, client credentials, scopes, redirect) behind an
`OIDC_ENABLED` flag with automatic discovery,
so that the installation can delegate login to my IdP without hard-coding endpoints, and the SPA can tell
whether SSO is available.

## Acceptance Criteria

1. **OIDC settings block.**
   Given `backend/config/settings/base.py` holds the DRF + auth config, when this story lands, then a settings
   block reads (from environment) `OIDC_ENABLED` (bool, default **false**), `OIDC_ISSUER` (the IdP issuer
   URL), `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_SCOPES` (default `"openid email profile"`), and
   `OIDC_REDIRECT_URI` (the backend callback, Story 17.2). Secrets come only from the environment — never
   committed (Control Constraint §7).
2. **Discovery, not hard-coded endpoints.**
   Given `OIDC_ISSUER`, when the OIDC config is resolved, then the authorization endpoint, token endpoint,
   JWKS URI, userinfo endpoint, and end-session endpoint are obtained from the issuer's
   `.well-known/openid-configuration` **discovery document** (IdP-agnostic) — the app does not hard-code any
   IdP-specific URL. Discovery results may be cached; a discovery failure is logged (structlog) and surfaced,
   not silently swallowed.
3. **Single installation-wide IdP.**
   Given the config, when interpreted, then it describes **one** operator-configured OP for the whole
   installation. **Per-org SSO is explicitly OUT of scope** (future work) — there is no per-org issuer.
4. **Flag gates everything.**
   Given `OIDC_ENABLED=false` (the default), when the app runs, then no OIDC routes/behavior are active and
   the app behaves exactly as today (local password auth only). Given `OIDC_ENABLED=true` **without** a valid
   issuer/client config, when the app starts (or on first use), then a clear configuration error is raised/
   logged — the flag never half-enables.
5. **Flag exposed to the SPA.**
   Given the SPA needs to know whether to show SSO before/without auth, when `GET /api/v1/config/` is called
   (`common/config_views.py::AppConfigView`, public + `AllowAny`), then the payload gains
   `"oidc_enabled": settings.OIDC_ENABLED` next to the existing `api_docs_enabled` (the object shape from
   Story 11.20 absorbs the new flag without a breaking change); `frontend/src/api/config.ts` `AppConfig`
   gains `oidc_enabled: boolean`.
6. **Dependency gate honored.**
   Given the new-dependency rule, when the RP library is needed, then it is added **only after** the user
   approves (see the GATE note); the story documents the proposal and does not assume approval.
7. **Tested; CI green.**
   Backend tests cover the flag default (false), the config endpoint carrying `oidc_enabled` in both states,
   and the misconfiguration error when enabled without issuer/client; a frontend test covers `getAppConfig`
   surfacing `oidc_enabled`. `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 0 — Dependency proposal (AC: #6)** — Propose `django-allauth` (authentication, Stories 17.1–17.5)
  and `authlib`/`PyJWT` (resource server, 17.6/17.7) to the user; do NOT edit `pixi.toml` /
  `backend/pyproject.toml` until approved.
- [ ] **Task 1 — Settings + flag (AC: #1, #3, #4)**
  - [ ] Add the OIDC block to `backend/config/settings/base.py` (env-driven; `OIDC_ENABLED` default false).
    Once the dep is approved, register `allauth`, `allauth.socialaccount`, and
    `allauth.socialaccount.providers.openid_connect` in `INSTALLED_APPS` and configure the OIDC provider (issuer
    → discovery, client id/secret, scopes) via allauth's `SOCIALACCOUNT_PROVIDERS`. `local.py` /
    `production.py` inherit; document the env vars.
  - [ ] Add a startup/first-use validation: enabled ⇒ issuer + client id/secret present, else raise
    `ImproperlyConfigured` (logged via structlog).
- [ ] **Task 2 — Discovery (AC: #2)**
  - [ ] Configure allauth's OIDC provider with the issuer so it resolves endpoints from
    `.well-known/openid-configuration` (allauth's OIDC provider consumes the discovery document). Discovery
    failure logged, not swallowed.
- [ ] **Task 3 — Expose the flag (AC: #5)**
  - [ ] `common/config_views.py::AppConfigView.get`: add `"oidc_enabled": settings.OIDC_ENABLED`.
  - [ ] `frontend/src/api/config.ts`: add `oidc_enabled: boolean` to `AppConfig`.
- [ ] **Task 4 — Tests (AC: #7)** — flag default, `/api/v1/config/` payload (both states), misconfig error,
  `getAppConfig` surfacing the flag. `pixi run ci` green.

## Dev Notes

### Fixed decisions (product owner)

- **App = OIDC Relying Party** (via **django-allauth**'s generic OIDC provider), not an identity provider.
  IdP-agnostic via **discovery** (`.well-known`). allauth is server-side/session-based, matching the BFF model.
- **Division of labor:** django-allauth handles **authentication** (Stories 17.1–17.5 + Epic 18's claim
  access); **authlib/PyJWT** handle the **resource-server** bearer/JWT validation on the API (17.6/17.7).
- **Single installation-wide IdP** — operator-configured issuer + client credentials. **Per-org SSO is OUT of
  scope** (future).
- **`OIDC_ENABLED` feature flag** — Phase 1 runs OIDC **alongside** local password auth (coexistence), and the
  flag is the switch. Default **false** so nothing changes until an operator opts in.
- **The `/api/v1/config/` endpoint is the SPA's flag channel** — reuse Story 11.20's public, unauth,
  object-shaped payload; it already exists to carry deploy-time flags to the SPA before login.

### Integration caveat (main risk)

django-allauth brings its own `SocialAccount` / `EmailAddress` models and its own URL + adapter conventions
that must be **reconciled with our existing** custom email-based `User` (`users/models.py`), our custom
`LoginView` (`django.contrib.auth` session login, `users/views.py:229`), and the **zero-org / active-org
session model** (Stories 2.6/2.18 + the session-carried active org, `users/auth.py`). Registering allauth's
apps + migrations alongside the current auth stack, and keeping our session/active-org semantics intact, is the
**primary integration risk** — budget for it here. Account linking must use the **verified** email
(`EmailAddress.verified` / the `email_verified` claim) to avoid account takeover (see Story 17.3).

### Current state (verified)

- DRF auth config + settings: `backend/config/settings/base.py:47-49`
  (`DEFAULT_AUTHENTICATION_CLASSES` = `OrgApiKeyAuthentication`, `SessionAuthentication`).
- Public config endpoint: `backend/generate_sbom/common/config_views.py::AppConfigView`
  (`authentication_classes = []`, `AllowAny`, returns `{"api_docs_enabled": ...}`); routed at
  `common/urls.py:8` (`config/`).
- Frontend config: `frontend/src/api/config.ts` (`AppConfig { api_docs_enabled }`, `getAppConfig()`);
  test `frontend/src/api/config.test.ts`.

### Testing standards

- Backend: pytest, DRF `APIClient`, `override_settings` to toggle `OIDC_ENABLED`. Frontend: Vitest, mock
  `apiRequest` (see `config.test.ts`).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.1: OIDC Provider Configuration, Discovery & Feature Flag]
- `backend/config/settings/base.py:47-49`, `backend/generate_sbom/common/config_views.py`, `common/urls.py:8`
- `frontend/src/api/config.ts`, `frontend/src/api/config.test.ts`
- Related: `11-20-api-docs-header-link.md` (the config-flag precedent)
- Downstream: `17-2-backend-oidc-login-bff-auth-code-pkce.md`, `17-5-frontend-sso-login.md`,
  `17-6-api-oauth2-resource-server.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
