# Story 18.2: Apply Mappings on Login (Provision/Sync Entitlements from Claims)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Second story of Epic 18 (Phase 2) — build after 18.1. DEPENDS ON EPIC 17.** Applies the validated
> claim→entitlement mapping (Story 18.1) **at login**: it provisions and syncs a user's org memberships +
> roles from their IdP claims each time they authenticate via OIDC. The precise **precedence/reconciliation**
> rules (override vs augment vs seed, drift, invariant preservation) are Story 18.3 — this story wires the
> application point and the happy-path sync; 18.3 pins the conflict semantics.

## Story

As an operator,
I want a user's org memberships and roles to be provisioned and kept in sync from their IdP groups/claims when
they log in via OIDC,
so that access is driven by the IdP as the source of truth for entitlements, without manual per-user role
management.

## Acceptance Criteria

1. **Applied at OIDC login.**
   Given the mapping is enabled (Phase 2 flag, operator-configured) and a user logs in via OIDC (Story 17.2
   allauth callback → Story 17.3 adapter user resolution), when login completes, then the mapping (Story 18.1)
   is evaluated against the user's claims (read from allauth's `SocialAccount.extra_data` / the adapter hook)
   and the resulting `(org, role)` entitlements (+ optional global-admin) are **applied** to their
   `OrgMembership`s on each login.
2. **Provision + sync (grant and revoke).**
   Given a user's IdP-derived entitlements change between logins, when they next log in, then the sync **adds**
   memberships/roles the claims now grant **and removes/downgrades** ones the claims no longer grant (subject
   to the precedence + drift rules of Story 18.3) — memberships are provisioned into **existing** orgs (Phase 2
   does not auto-create orgs; org creation stays global-admin-only, Story 2.12).
3. **Zero-org still possible.**
   Given a user whose claims map to **no** entitlement, when they log in, then they remain (or become) a
   **zero-org** user (Story 2.6/17.3) and land on Home (Story 2.18) — IdP login never forces an org, and an
   empty/absent groups claim does not error.
4. **Invariants preserved on application.**
   Given the guarded invariants (last-admin per org, last-global-admin overall; Stories 2.9/2.16/13.1), when a
   sync would remove/downgrade the last admin of an org or the last global admin, then the application path
   **preserves the invariant** (does not strip the last admin/global-admin) and logs the skipped change — the
   exact rule is owned by Story 18.3; this story must call into it, not bypass it.
5. **Atomic + audited.**
   Given a login sync, when it runs, then the membership changes for that user apply in a single transaction
   (no partially-synced user on failure) and each grant/revoke/skip is logged (structlog) with user + claim
   provenance for audit.
6. **Idempotent.**
   Given unchanged claims, when the user logs in repeatedly, then the sync is **idempotent** — no spurious
   membership writes, no thrash.
7. **Tested; CI green.**
   Backend tests cover: first OIDC login with mapped groups → correct memberships/roles; changed claims →
   add + remove/downgrade; empty claims → zero-org (no error); invariant-preserving skip (last admin / last
   global-admin not stripped, logged); atomicity; idempotency on repeat login. `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Application hook (AC: #1)** — call the entitlement sync from the OIDC login path (an allauth
  adapter hook / `user_logged_in` signal, after Story 17.3 resolves the user) when Phase 2 is enabled; feed it
  the claims from `SocialAccount.extra_data`.
- [ ] **Task 2 — Sync service (AC: #2, #3, #6)** — `sync_entitlements(user, claims)`: compute target
  entitlements (Story 18.1 mapping), diff against current memberships, add/remove/downgrade into **existing**
  orgs; idempotent; zero-org allowed.
- [ ] **Task 3 — Invariant + precedence hook (AC: #4)** — delegate every remove/downgrade decision to Story
  18.3's reconciliation rule so guarded invariants hold; log skips.
- [ ] **Task 4 — Atomicity + audit (AC: #5)** — one transaction; structlog provenance.
- [ ] **Task 5 — Tests (AC: #7)** — see ACs.
- [ ] `pixi run ci` green.

## Dev Notes

### Fixed decisions (product owner)

- **IdP-driven entitlements, applied at login.** Phase 2's whole point: memberships/roles are provisioned and
  synced from claims on each OIDC login. Depends on Epic 17's validated claims + Story 18.1's mapping.
- **Provision into existing orgs only.** No auto org creation (Story 2.12 keeps org creation global-admin-only).
- **Zero-org preserved.** No-entitlement claims → a zero-org user (Story 2.6/17.3), never a forced org.
- **Invariants + precedence are Story 18.3's contract.** This story applies changes but **routes every
  remove/downgrade through 18.3's reconciliation** — it never strips the last admin/global-admin on its own.

### Current state (verified)

- User resolution at login: Story 17.3 (allauth `SocialAccount` `(iss, sub)` → `User`, via the adapter), from
  Story 17.2's allauth callback; claims live in `SocialAccount.extra_data`.
- Membership/roles: `OrgMembership.Role` (`users/models.py:89-94`) member/manager/admin; global-admin ADMIN org
  (Story 2.8). Org creation global-admin-only (Story 2.12). Zero-org (Story 2.6) → Home (Story 2.18).
- Guarded invariants: Stories 2.9 / 2.16 / 13.1 (last-admin, protect-global-admin).
- Mapping + preview: Story 18.1.

### Testing standards

- Backend: pytest `@pytest.mark.django_db`; drive `sync_entitlements` with sample claim sets across logins;
  assert membership diffs, zero-org case, invariant-preserving skips, atomicity (mock a mid-sync failure), and
  idempotency (identical state after a repeat run).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 18.2: Apply Mappings on Login]
- `backend/generate_sbom/users/models.py:89-94`, `2-6-zero-org-users-and-identity-decoupling.md`,
  `2-12-restrict-org-creation-to-global-admins.md`, `2-18-restrict-zero-org-users-to-home.md`
- Depends on: `18-1-claim-group-to-role-mapping-configuration.md`, Epic 17 (esp. `17-2`/`17-3`)
- Downstream / paired: `18-3-precedence-and-reconciliation.md` (owns the conflict/invariant rules this story
  calls into)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
