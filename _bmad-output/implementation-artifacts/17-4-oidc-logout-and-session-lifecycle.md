# Story 17.4: OIDC Logout & Session Lifecycle

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Fourth story of Epic 17 — build after 17.3.** Rounds out the session lifecycle for OIDC: RP-initiated
> logout, Django session invalidation, and the refresh/expiry behavior of the server-side session (the BFF
> holds the tokens; the browser holds only the session cookie). Depends on Stories 17.1–17.3.

## Story

As an OIDC-authenticated user,
I want logging out of the app to end my session cleanly (and optionally at the IdP),
so that my authenticated session doesn't outlive my intent, and returning requires a fresh login.

## Acceptance Criteria

1. **Local session invalidation on logout.**
   Given an OIDC-authenticated session, when the user logs out (e.g. `POST /api/v1/auth/oidc/logout/`, or the
   existing `LogoutView` path unified), then Django `logout()` is called — the session is flushed and the
   session cookie cleared — and any server-side-retained OIDC tokens for that session are discarded. The
   result is indistinguishable from a local logout from the SPA's perspective (still session/cookie-based).
2. **RP-initiated logout (optional, discovery-driven).**
   Given the IdP publishes an `end_session_endpoint` (discovery, Story 17.1), when the user logs out and
   RP-initiated logout is enabled, then the backend redirects the browser to the IdP end-session endpoint
   (with `id_token_hint` / `post_logout_redirect_uri` as the IdP requires) so the IdP session also ends. If
   the IdP has no end-session endpoint, local logout still fully succeeds (graceful degradation, logged).
3. **Session expiry mirrors policy.**
   Given the server-side session, when it is established (Story 17.2), then its lifetime follows Django's
   session settings (the app's existing policy) — the browser cookie is the session; the OIDC access/refresh
   tokens are custody of the BFF, never the browser.
4. **Refresh behavior is explicit.**
   Given an OIDC session whose retained access token expires while the Django session is still valid, when the
   next request needs the token (relevant only if the app calls the IdP/userinfo on the user's behalf), then
   the documented behavior is one of: (a) silent refresh via the stored refresh token server-side, or (b) no
   refresh — the Django session is the source of truth and the app does not call the IdP mid-session. The
   chosen rule is stated, implemented, and tested (Phase-1 default: **(b)** — the session, not a live IdP
   token, drives authorization, so no mid-session refresh is required).
5. **Coexistence.**
   Given local and OIDC login run side by side (`OIDC_ENABLED`, Story 17.8), when either kind of user logs
   out, then logout works for both; a local-password session logout is unchanged; OIDC-specific steps (token
   discard, optional RP-initiated redirect) run only for OIDC sessions.
6. **Tested; CI green.**
   Backend tests cover: logout flushes the session + clears retained tokens; RP-initiated redirect built when
   `end_session_endpoint` exists and skipped (local-only) when it doesn't; a local-password logout still works;
   the documented refresh rule. `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Logout flow (AC: #1, #5)** — unify/extend `LogoutView` so OIDC sessions also discard retained
  tokens; `logout()` flushes the session for both kinds.
- [ ] **Task 2 — RP-initiated logout (AC: #2)** — if `end_session_endpoint` present, build the redirect;
  else local-only. Log the branch taken.
- [ ] **Task 3 — Lifecycle/refresh policy (AC: #3, #4)** — implement + document the Phase-1 rule (default: no
  mid-session refresh; session is the source of truth).
- [ ] **Task 4 — Tests (AC: #6)** — see ACs.
- [ ] `pixi run ci` green.

## Dev Notes

### Fixed decisions (product owner)

- **BFF/session, still cookie-based.** Logout is fundamentally a Django-session logout (`logout()`); OIDC adds
  discarding server-held tokens (allauth's `SocialToken`/session state) and an optional RP-initiated redirect to
  the IdP using the discovery `end_session_endpoint`.
- **Discovery-driven, graceful.** RP-initiated logout is used only if the IdP advertises an end-session
  endpoint; absence must not break local logout.
- **Phase-1 refresh default = none.** The Django session drives authorization (roles are app-managed,
  Story 17.3); the app does not depend on a live IdP token mid-session, so no silent refresh is required in
  Phase 1. State the rule explicitly so Epic 18 (which reads claims at login) has a known baseline.

### Current state (verified)

- Logout precedent: `backend/generate_sbom/users/views.py::LogoutView` (`:269`) calls `logout()` (`:275`).
- Session establishment: Story 17.2 (`login()` + session cookie + csrf).
- Discovery (`end_session_endpoint`): Story 17.1.

### Testing standards

- Backend: pytest + DRF `APIClient`; assert the session is flushed (subsequent `auth/me` is 401/403) and the
  RP-initiated redirect is/ isn't built based on a mocked discovery doc.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.4: OIDC Logout & Session Lifecycle]
- `backend/generate_sbom/users/views.py:269-283` (`LogoutView`)
- Related: `17-1-oidc-provider-configuration-and-discovery.md`,
  `17-2-backend-oidc-login-bff-auth-code-pkce.md`, `17-3-jit-user-provisioning-and-account-linking.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
