# Story 17.3: JIT User Provisioning & Account Linking

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Third story of Epic 17 — build after 17.2.** Turns a validated `id_token` (Story 17.2's callback) into a
> local `User`. **First OIDC login provisions a zero-org user** (preserving Story 2.6's identity-decoupling
> invariant), links to an existing local user by **verified email**, and persists the OIDC subject
> (`sub`) ↔ user mapping so subsequent logins re-resolve the same account. **Authorization stays app-managed
> in Phase 1** — no roles/memberships come from the IdP here (that is Epic 18).

> **Depends on Story 17.2** (it runs during allauth's callback, after `id_token` validation).

> **Implemented via django-allauth adapter hooks (Story 17.1's proposed dep).** JIT zero-org provisioning,
> account-linking-by-verified-email, and persisting `(iss, sub)` ↔ user are done through allauth's
> `DefaultSocialAccountAdapter` — override **`pre_social_login`** (link to an existing local user by verified
> email; block takeover) and **`save_user`** (provision the zero-org user with an unusable password), and/or the
> **`user_signed_up`** signal. allauth's own `SocialAccount` already stores the provider `sub` + `extra_data`
> (the Epic 18 claims access point); this story reconciles that with our custom `User` and zero-org model.

## Story

As an operator,
I want a first-time OIDC user to get a local account automatically, and a returning user to resolve to the same
account,
so that people can sign in via the IdP without a separate manual account-creation step, while the app keeps
owning org membership and roles.

## Acceptance Criteria

1. **Persist `sub` ↔ user (via allauth `SocialAccount`).**
   Given a validated `id_token` with a stable subject (`sub`) and issuer (`iss`), when a user logs in, then the
   `(iss, sub)` identifier is persisted and associated with a local `User` — using allauth's `SocialAccount`
   (`provider` + `uid` = the `sub`), whose `extra_data` also retains the claims for Epic 18 — so a later login
   with the same `sub` **re-resolves the same account** (the `sub`, not the email, is the durable key — emails
   can change).
2. **First login → zero-org user (preserve Story 2.6).**
   Given a `sub` never seen before **and** no existing local user matching the verified email, when they log
   in, then a **new `User` is provisioned with ZERO org memberships** — the Story 2.6 identity-decoupling
   invariant holds: a user exists independent of any org and lands on Home until an admin adds them
   (Story 2.18). No org is auto-created (org creation stays global-admin-only, Story 2.12).
3. **Account linking by verified email.**
   Given a `sub` never seen before **but** an existing local `User` whose email matches the token's **verified**
   email (`email_verified == true` claim), when they log in, then the OIDC identity is **linked** to that
   existing user (store `(iss, sub)` on them) rather than creating a duplicate — the user keeps their existing
   org memberships and roles. If the email is present but **not** verified, it is **not** used for linking
   (a new zero-org user is provisioned, or the login is rejected per the conflict rule below).
4. **Conflict / edge handling.**
   Given ambiguous or conflicting identity, when resolving, then the rules are explicit and tested:
   (a) a `sub` already linked to user A but arriving with a different email → still resolves to **A** (sub
   wins; email is not re-linked automatically); (b) a verified email matching an existing user who is
   **already linked to a different `sub`** → **reject** the login with a clear, logged error (no silent
   account takeover); (c) missing/absent email claim → provision a zero-org user keyed on `sub` only (or
   reject if the installation requires email — operator-documented). No path silently merges two distinct
   accounts.
5. **Authorization unchanged (Phase 1 boundary).**
   Given provisioning/linking, when it completes, then **no org membership or role is granted, changed, or
   read from the IdP** — roles stay member/manager/admin/global-admin, entirely app-managed. Mapping IdP
   groups/claims → entitlements is **Epic 18** and explicitly out of scope here.
6. **Provisioning is atomic + attributed.**
   Given first-login provisioning, when it runs, then user creation + `sub` linking happen in a single DB
   transaction (no half-provisioned user on failure), the user is created with an **unusable password** (they
   authenticate via OIDC, not locally), and the event is logged (structlog) with the `sub`/email for audit.
7. **Tested; CI green.**
   Backend tests cover: new `sub` + no email match → zero-org user (0 memberships); new `sub` + verified-email
   match → linked to existing user (memberships preserved, no duplicate); returning `sub` → same user; email
   present but unverified → not linked; conflict (b) → rejected; unusable password set; provisioning atomic.
   `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Identity via allauth (AC: #1)** — use allauth's `SocialAccount` (provider + `uid` = `sub`) as
  the `(iss, sub)` ↔ `User` link (its migrations come with the app — reconcile with our custom `User`).
- [ ] **Task 2 — Adapter resolution (AC: #2, #3, #4, #6)** — a `SocialAccountAdapter` subclass overriding
  `pre_social_login` (link to an existing `User` by **verified** email; conflict rules) and `save_user`
  (provision zero-org, Story 2.6, unusable password); atomic; structlog. Runs inside Story 17.2's callback.
- [ ] **Task 3 — Boundary guard (AC: #5)** — assert no membership/role writes in the adapter (Phase 1); the
  claims in `SocialAccount.extra_data` are the clean extension seam for Epic 18.
- [ ] **Task 4 — Tests (AC: #7)** — see ACs.
- [ ] `pixi run ci` green.

## Dev Notes

### Fixed decisions (product owner)

- **Implemented via allauth adapter hooks.** JIT provisioning + linking + `(iss, sub)` persistence go through
  allauth's `DefaultSocialAccountAdapter` (`pre_social_login`, `save_user`) and/or the `user_signed_up` signal,
  backed by allauth's `SocialAccount`/`EmailAddress` — not a bespoke user resolver.
- **JIT provisioning, zero-org first.** First OIDC login creates a **zero-org user** — this deliberately
  preserves Story 2.6 (identity decoupled from org membership; a user can exist with no org and only reach
  Home). OIDC does not auto-create or auto-join any org.
- **Link by VERIFIED email; key on `sub`.** Account linking to an existing local user uses the **verified**
  email only (`EmailAddress.verified` / `email_verified` claim, checked in `pre_social_login`); the durable
  identifier is the OIDC **`sub`** (emails change, subs don't). Verified-only linking is the takeover guard.
- **Authorization stays app-managed (Phase 1).** No roles/memberships derive from the IdP. Claims→entitlements
  is **Epic 18** (reading `SocialAccount.extra_data`), which depends on this story shipping. Keep the seam;
  do not build it here.
- **No silent account takeover.** A verified email colliding with a `User` already linked to a different `sub`
  is a hard reject, logged — never an automatic merge.
- **Integration caveat (see Story 17.1).** allauth's `SocialAccount`/`EmailAddress` models + adapter/URL
  conventions must be reconciled with our custom `User`, custom `LoginView`, and zero-org/active-org session —
  the main integration risk.

### Current state (verified)

- Zero-org invariant: Story 2.6 (`2-6-zero-org-users-and-identity-decoupling.md`) — a user exists without any
  `OrgMembership`; Story 2.18 restricts zero-org users to Home.
- User model: `backend/generate_sbom/users/models.py` — email-based `User` (`:53-66`, `email` unique,
  `USERNAME_FIELD = "email"`), `OrgMembership` with `Role` ADMIN/MEMBER (`:89-94`) + MANAGER (Story 16.1).
- Org creation is global-admin-only (Story 2.12) — OIDC provisioning must not create orgs.
- Called from: Story 17.2's callback, after `id_token` validation (the validated claims are the input).

### Testing standards

- Backend: pytest `@pytest.mark.django_db`; drive the adapter (`pre_social_login`/`save_user`) with sample
  sociallogin/claim fixtures; assert membership counts and the `SocialAccount` `(provider, uid)` row; assert
  `has_usable_password()` is false on provisioned users; assert unverified-email logins are not linked.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.3: JIT User Provisioning & Account Linking]
- `backend/generate_sbom/users/models.py:53-94` (User/OrgMembership), `2-6-zero-org-users-and-identity-decoupling.md`,
  `2-18-restrict-zero-org-users-to-home.md`, `2-12-restrict-org-creation-to-global-admins.md`
- Related: `17-2-backend-oidc-login-bff-auth-code-pkce.md`
- Downstream (depends on this): Epic 18 (`18-1`…`18-3`) maps claims → entitlements

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
