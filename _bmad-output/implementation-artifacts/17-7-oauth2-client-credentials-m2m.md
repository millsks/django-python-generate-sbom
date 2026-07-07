# Story 17.7: OAuth2 Client-Credentials for Machine-to-Machine

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Resource-server track of Epic 17 — build after 17.6.** Lets CI/automation obtain and use **OAuth2
> client-credentials** access tokens for machine-to-machine API access, **coexisting with org API keys** so
> automation can migrate off keys without a hard cutover. Builds directly on Story 17.6's bearer/JWT
> resource-server validation.

> **⚠ SECURITY-CRITICAL story.** M2M tokens carry no interactive user; the org/scope a machine token grants
> must be pinned and validated. See "Security acceptance criteria".

## Story

As an operator running CI/automation,
I want my automation to authenticate to the API with an OAuth2 client-credentials token,
so that machine access uses standard OAuth2 (issued and revocable at the IdP) instead of a long-lived org API
key, while existing keys keep working during the transition.

## Acceptance Criteria

1. **Client-credentials tokens accepted.**
   Given a machine obtains an access token from the IdP via the **client-credentials grant** (its own client
   id/secret, no user), when it calls the API with `Authorization: Bearer <token>`, then Story 17.6's
   resource-server validation accepts it (signature/JWKS, `iss`, `aud`, `exp`, scopes) and the request is
   authenticated as a **machine principal**.
2. **Machine → org/scope mapping.**
   Given a client-credentials token has **no user subject**, when the caller/org is resolved, then the
   **active org** and the permitted scope are derived deterministically from the token's claims (e.g. an
   `org`/audience/`client_id`→org mapping the operator configures), so `get_request_org`/`get_admin_org`
   resolve correctly and AD-2 org isolation holds — a machine token scoped to org A can never act on org B.
3. **No implicit privilege.**
   Given a machine principal, when it acts, then it gets **only** the access its mapping grants (e.g. member-
   level API access to its org by default) — a client-credentials token does not confer admin/global-admin
   unless the operator's mapping explicitly does, and even then authorization flows through the existing
   permission gates (Story 17.6 AC #4). No entitlements are invented here (Epic 18 owns claims→roles).
4. **Coexistence with API keys.**
   Given org API keys still work (Story 2.4 / `OrgApiKeyAuthentication`), when automation runs, then it may use
   **either** an API key **or** a client-credentials bearer token — both paths reach the same API with the same
   org scoping. Nothing about the API-key path changes; this is a *second* machine-auth option, enabling the
   migration in Story 17.8.
5. **Operator documentation.**
   Given an operator wants to move CI off keys, when they read the story's operator notes, then they have the
   concrete steps: register a machine client at the IdP, configure the `client_id`→org/scope mapping, obtain a
   token via client-credentials, and call the API with the bearer token (planning-level guidance; no `docs/**`
   edits — this lands in Story 17.8's rollout docs).
6. **Tested; CI green.**
   Backend tests cover: a client-credentials token (no user sub) authenticates as a machine principal mapped
   to the correct org; org isolation (token for org A rejected/scoped-out on org B); default access is
   non-admin; an API-key request still works unchanged; invalid/expired M2M tokens → 401. `pixi run ci` green.

## Security acceptance criteria (restated, must all hold)

- The **org/scope** a machine token grants is derived from validated token claims + operator mapping — never
  inferred loosely; a token for one org must not act on another (AD-2).
- **No privilege escalation**: default machine access is non-admin; elevation only via explicit operator
  mapping, still subject to existing permission gates.
- All Story 17.6 bearer validations apply (signature/JWKS, `iss`, `aud`, `exp`, scopes); failures → 401.
- Client secrets for machine clients live at the IdP / in operator env — never committed (§7).

## Tasks / Subtasks

- [ ] **Task 1 — Machine principal (AC: #1, #2, #3)** — extend Story 17.6's resolution to handle a no-user
  (client-credentials) token: resolve org/scope from claims + operator mapping; represent a machine principal
  distinctly from a user; default non-admin.
- [ ] **Task 2 — Org-scope mapping (AC: #2)** — a configurable `client_id`/audience → org (+ scope) mapping;
  enforce AD-2 isolation.
- [ ] **Task 3 — Coexistence (AC: #4)** — verify the API-key path is untouched and both machine paths work.
- [ ] **Task 4 — Tests (AC: #6)** — see ACs; mock the IdP token/JWKS.
- [ ] `pixi run ci` green.

## Dev Notes

### Fixed decisions (product owner)

- **OAuth2 M2M coexists with API keys.** Client-credentials is **added** so CI/automation can move off keys;
  **API keys keep working** throughout. The actual deprecation of keys is planned in Story 17.8, not forced
  here.
- **Machine principal, tightly scoped.** A client-credentials token has no user; its org + scope come from
  validated claims and an operator mapping, default non-admin, AD-2-isolated. Authorization still flows through
  existing gates (no entitlements from the token — Epic 18 owns that).
- **Builds on 17.6 (authlib/PyJWT, not allauth).** All bearer validation is Story 17.6's authlib/PyJWT
  resource-server path — django-allauth (the login library) plays no part on the API side. This story adds only
  the no-user (client-credentials) resolution + org/scope mapping on top of 17.6.

### Current state (verified)

- Resource-server validation: Story 17.6 (`OAuth2ResourceServerAuthentication`).
- API-key path (the thing being coexisted with, eventually migrated off): Story 2.4,
  `backend/generate_sbom/users/authentication.py::OrgApiKeyAuthentication`; org on `request.auth.org`;
  `users/auth.py::get_request_org`/`get_admin_org`.
- AD-2 (org isolation) is the invariant machine scoping must preserve.

### Testing standards

- Backend: pytest + DRF `APIClient`; craft a client-credentials-style token (no `sub`, with org/scope claims);
  mock validation; assert org resolution + isolation + non-admin default; assert API-key path unchanged.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.7: OAuth2 Client-Credentials for Machine-to-Machine]
- `backend/generate_sbom/users/authentication.py`, `backend/generate_sbom/users/auth.py`, `2-4-api-key-management.md`
- Related: `17-6-api-oauth2-resource-server.md`
- Downstream: `17-8-coexistence-flag-rollout-and-cutover.md` (plans the API-key deprecation)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
