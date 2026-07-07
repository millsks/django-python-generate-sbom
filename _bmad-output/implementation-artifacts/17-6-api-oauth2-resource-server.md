# Story 17.6: API as OAuth2 Resource Server (Bearer/JWT Validation)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Resource-server track of Epic 17 — build in parallel with 17.2–17.5 (needs 17.1's config/discovery).**
> Makes the DRF API an **OAuth2 Resource Server**: it validates OAuth2/JWT **bearer** access tokens (JWKS from
> the IdP) **alongside** the existing API-key and session authentication — an *additive* authentication class,
> not a replacement. Permissions/authorization are unchanged. Story 17.7 (client-credentials M2M) builds on
> this to let automation obtain those tokens.

> **⚠ SECURITY-CRITICAL story.** Bearer-token validation (signature/JWKS, `iss`, `aud`, `exp`, scopes) is the
> acceptance contract — see "Security acceptance criteria".

> **⚠ NEW RUNTIME DEPENDENCY — GATE.** JWT/JWKS validation uses **`authlib` or `PyJWT`** (proposed in Story
> 17.1) — **NOT django-allauth.** allauth is the **authentication** (login/RP) library; it does **not** validate
> incoming OAuth2 bearer/JWT tokens on the API. This resource-server half is a separate concern owned by
> authlib/PyJWT. Do not add the dependency until the user approves (Story 17.1 GATE).

## Story

As an API client or automation,
I want to call the DRF API with an OAuth2 bearer token instead of (or alongside) an org API key,
so that machine access can move onto standards-based OAuth2 while existing API keys keep working unchanged.

## Acceptance Criteria

1. **New authentication class, additive.**
   Given `DEFAULT_AUTHENTICATION_CLASSES` currently lists `OrgApiKeyAuthentication` + `SessionAuthentication`
   (`config/settings/base.py:47-49`), when this story lands, then a new
   `OAuth2ResourceServerAuthentication` (bearer/JWT) is **added** to that list — API-key and session auth
   continue to work exactly as before (no removal, no behavior change to existing paths).
2. **Bearer-token validation.**
   Given a request with `Authorization: Bearer <access_token>`, when authenticated, then the access token is
   validated: signature against the IdP **JWKS** (discovery, Story 17.1), `iss` == configured issuer, `aud`
   (or resource/audience) == the configured API audience, `exp`/`nbf` within skew. Any failure → **401**
   (`WWW-Authenticate: Bearer`), logged with a specific exception type (never swallowed). A JWT (self-
   contained) validation path is the default; if the IdP issues opaque tokens, introspection is the documented
   alternative.
3. **Token → user/org mapping.**
   Given a validated token, when the caller is resolved, then the token's subject maps to the local `User`
   (reusing the Story 17.3 `(iss, sub)` link where it is a user token), and the **active org** is resolved for
   the request so `get_request_org` / `get_admin_org` (`users/auth.py`) keep returning the right org — the same
   way the API-key path sets `request.auth.org` today. For a machine (client-credentials, Story 17.7) token
   with no user subject, the org/identity is resolved from the token's claims/mapping (defined precisely in
   17.7).
4. **Permissions unchanged.**
   Given the existing DRF permissions/authorization (admin gates, org scoping, AD-2 isolation), when a
   bearer-authenticated request runs, then **authorization is unchanged** — the new class only *authenticates*;
   who-can-do-what still flows through the existing permission classes and `get_admin_org`/role checks. A
   bearer token does not grant more than the mapped user/org already has.
5. **Coexistence + precedence.**
   Given multiple auth schemes, when a request carries a bearer token, then the OAuth2 class handles it; an
   `Api-Key` request still hits `OrgApiKeyAuthentication`; a browser session still hits
   `SessionAuthentication`. The classes are ordered so each scheme is unambiguously matched (documented), and
   `OIDC_ENABLED=false` leaves the API exactly as today.
6. **Tested; CI green.**
   Backend tests cover: a valid bearer token authenticates and maps to the right user/org; each validation
   failure (bad signature, wrong `iss`, wrong `aud`, expired) → 401; API-key and session requests are
   unaffected; permissions still enforce admin/org scoping under bearer auth; flag-off leaves behavior
   unchanged. `pixi run ci` green.

## Security acceptance criteria (restated, must all hold)

- **Signature** verified against the IdP **JWKS** (fetched via discovery; keys cached with rotation handling).
- **`iss`** == configured issuer; **`aud`** == the configured API audience/resource; **`exp`/`nbf`** within
  skew.
- **Scope/audience** checked so a token minted for another audience is rejected.
- Failures return **401** with `WWW-Authenticate: Bearer`, logged with a specific exception type — never a
  bare `except`, never silently downgraded to anonymous.
- The class **authenticates only**; existing permission/authorization logic is untouched (no privilege
  escalation via bearer).

## Tasks / Subtasks

- [ ] **Task 1 — Auth class (AC: #1, #2, #5)** — `OAuth2ResourceServerAuthentication(BaseAuthentication)` in
  `users/authentication.py` (next to `OrgApiKeyAuthentication`): parse `Bearer`, validate JWT via JWKS,
  `authenticate_header` → `Bearer`. Add it to `DEFAULT_AUTHENTICATION_CLASSES` (`config/settings/base.py:47`).
- [ ] **Task 2 — User/org resolution (AC: #3, #4)** — map validated token → `User` (via `(iss, sub)`) + active
  org so `get_request_org`/`get_admin_org` work; keep permissions untouched.
- [ ] **Task 3 — JWKS handling** — fetch/cache JWKS from discovery (Story 17.1); handle key rotation; log
  failures.
- [ ] **Task 4 — Tests (AC: #6)** — see ACs; mock the IdP JWKS (no live network).
- [ ] `pixi run ci` green.

## Dev Notes

### Fixed decisions (product owner)

- **Division of labor: authlib/PyJWT here, not allauth.** django-allauth handles **authentication** (the OIDC
  login/RP flow, Stories 17.1–17.5); it does **not** validate incoming OAuth2 bearer/JWT tokens on the API. So
  the resource-server JWKS/JWT validation in this story is built on **`authlib` or `PyJWT`** — a distinct
  dependency and concern from the login side.
- **Additive, not rip-and-replace.** OAuth2 resource-server auth is **added** to the DRF authentication
  classes **alongside** the existing `OrgApiKeyAuthentication` and `SessionAuthentication`. **API keys keep
  working.** This is coexistence, mirroring the login side.
- **Authenticate only; authorization stays app-managed.** The class resolves identity/org; existing permission
  classes and role/admin gates decide access. No entitlements come from the token in Phase 1 (Epic 18).
- **Mirror the API-key pattern.** Resolve the active org onto the request the same way the API-key path does
  (`request.auth.org`) so downstream `get_request_org`/`get_admin_org` are unchanged.

### Current state (verified)

- DRF auth: `backend/config/settings/base.py:47-49` (`OrgApiKeyAuthentication`, `SessionAuthentication`).
- API-key precedent: `backend/generate_sbom/users/authentication.py::OrgApiKeyAuthentication` (`:29`),
  `_KEYWORD = "Api-Key"` (`:25`), `authenticate_header` → `WWW-Authenticate` (`:48`).
- Org resolution: `backend/generate_sbom/users/auth.py::get_request_org` (`:20`, branches API-key vs session),
  `get_admin_org` (`:64`).
- `(iss, sub)` ↔ user link: Story 17.3. Discovery/JWKS/config: Story 17.1.

### Testing standards

- Backend: pytest + DRF `APIClient` with an `Authorization: Bearer` header; mock the JWKS/validation; assert
  the resolved user/org and 401s; assert API-key and session requests still behave identically.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.6: API as OAuth2 Resource Server]
- `backend/config/settings/base.py:47-49`, `backend/generate_sbom/users/authentication.py:25-49`,
  `backend/generate_sbom/users/auth.py:20-64`
- Related: `17-1-oidc-provider-configuration-and-discovery.md`,
  `17-3-jit-user-provisioning-and-account-linking.md`, `2-4-api-key-management.md`
- Downstream: `17-7-oauth2-client-credentials-m2m.md`, `17-8-coexistence-flag-rollout-and-cutover.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
