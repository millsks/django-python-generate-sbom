# Story 18.3: Precedence & Reconciliation (IdP vs App-Managed Entitlements)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Third story of Epic 18 (Phase 2) — build after 18.2. DEPENDS ON EPIC 17.** Defines the explicit rule for
> **how IdP-driven entitlements reconcile with app-managed roles** — override / augment / seed — including
> drift handling and, critically, how the guarded invariants (last-admin, last-global-admin) are **preserved**
> under IdP-sourced changes. Story 18.2 applies mappings; **this story owns the conflict semantics 18.2 calls
> into.**

## Story

As an operator,
I want a precise, documented precedence rule for when IdP claims and app-managed roles disagree,
so that entitlement sync is predictable, never strips protected access, and I know exactly whether the IdP
overrides, augments, or merely seeds a user's roles.

## Acceptance Criteria

1. **Precedence mode is explicit and configured.**
   Given IdP-derived and app-managed entitlements can differ, when reconciliation runs, then the behavior is
   one **explicitly configured** mode, documented and tested:
   - **seed** — IdP claims set entitlements only on **first** provision; later app-managed changes win (IdP
     never revokes afterward);
   - **augment** — IdP claims can **add** entitlements but never remove app-granted ones (union; IdP is
     additive);
   - **override** — IdP claims are the **source of truth**; app-managed roles that aren't backed by a claim are
     removed/downgraded on sync (with the invariant guard, AC #3).
   The default mode is stated (recommended: **augment**, the least-surprising, non-destructive default).
2. **Drift handling.**
   Given a user's app-managed roles drift from their claims between logins (an admin manually changed a role,
   or the IdP groups changed), when they next log in, then the drift is reconciled per the configured mode
   deterministically, and each reconciliation decision (kept / added / removed / skipped) is logged (structlog)
   with the reason, so an operator can audit *why* a user's access changed.
3. **Invariants always preserved (over every mode).**
   Given the guarded invariants — an org must keep **≥1 admin** (Stories 2.9/2.16) and the platform must keep
   **≥1 global-admin** (Stories 2.8/13.1) — when reconciliation (in **any** mode, including override) would
   remove/downgrade the last admin of an org or the last global admin, then the change is **refused/skipped**,
   the prior state is kept, and a warning is logged. The invariant **wins over the IdP** — no claim change can
   strip the last admin/global-admin.
4. **App-managed manual actions still work.**
   Given the app's manual role management (promote/demote, add/remove by email — Stories 2.16/2.20/2.7/16.1),
   when Phase 2 is on, then those actions still function; how they interact with the next sync is defined by
   the mode (seed: manual wins; augment: manual adds persist, IdP adds too; override: IdP re-asserts on next
   login, except where an invariant protects the manual state).
5. **Global-admin sourcing is guarded.**
   Given global-admin is the most powerful tier, when a claim maps to global-admin, then granting it via IdP is
   allowed only if the operator explicitly opts in (a claim→global-admin mapping is deliberate, Story 18.1),
   and **revoking** the last global-admin via a claim change is refused (AC #3). Global-admin remains
   auditable via the Story 13.1 screen regardless of source.
6. **Reconciliation is pure + testable.**
   Given a current membership state + a target entitlement set + a mode, when reconciliation computes the diff,
   then it is a **pure function** (`reconcile(current, target, mode) -> planned_changes`) that Story 18.2
   applies transactionally — so precedence, drift, and invariant preservation are unit-testable without a login
   round-trip.
7. **Tested; CI green.**
   Backend tests cover each mode (seed/augment/override) on the same drift scenario producing the documented
   result; the invariant guard refusing to strip the last admin and last global-admin **in override mode**;
   manual-action interaction per mode; global-admin opt-in + last-global-admin protection; the pure
   `reconcile` diff. `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Precedence modes (AC: #1, #4)** — define + configure seed / augment / override; default
  augment; document manual-action interaction per mode.
- [ ] **Task 2 — `reconcile` pure function (AC: #6, #2)** — `reconcile(current, target, mode) -> changes`;
  deterministic; emits a decision log per entitlement.
- [ ] **Task 3 — Invariant guard (AC: #3, #5)** — refuse any change (any mode) that would strip the last admin
  of an org or the last global-admin; reuse the existing guard logic (Stories 2.16/2.9/13.1); global-admin
  grant requires explicit opt-in.
- [ ] **Task 4 — Wire into 18.2 (AC: #6)** — Story 18.2's `sync_entitlements` calls `reconcile` and applies the
  plan transactionally.
- [ ] **Task 5 — Tests (AC: #7)** — see ACs.
- [ ] `pixi run ci` green.

## Dev Notes

### Fixed decisions (product owner)

- **One explicit precedence rule.** override / augment / seed — the operator picks; default **augment**
  (additive, non-destructive). Ambiguity here is the main Phase-2 risk, so the mode is explicit and tested.
- **Invariants beat the IdP.** In **every** mode, last-admin / last-global-admin protections hold — a claim
  change can never strip protected access. This is the hard safety rule.
- **Global-admin via IdP is opt-in.** Sourcing the platform tier from a claim is deliberate (Story 18.1), and
  its last-holder is protected (Story 13.1 / AC #3).
- **Pure reconciliation.** The diff is a pure function 18.2 applies — precedence/drift/invariants are unit-
  testable in isolation.

### Current state (verified)

- Guarded invariants: last-admin/edge cases (Story 2.9), promote/protect-global-admin (Story 2.16), demote
  (Story 2.20), global-admin management (Story 13.1); manager role (Story 16.1); add/remove by email
  (Story 2.7). Roles: `OrgMembership.Role` (`users/models.py:89-94`).
- Application point: Story 18.2 `sync_entitlements`; mapping/preview: Story 18.1; claims/identity: Epic 17.

### Testing standards

- Backend: pytest; table-driven tests over the three modes × a fixed drift scenario; explicit last-admin /
  last-global-admin override-mode cases; assert `reconcile` purity (no DB writes) separately from 18.2's
  transactional application.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 18.3: Precedence & Reconciliation]
- `backend/generate_sbom/users/models.py:89-94`, `2-9-membership-edge-cases.md`,
  `2-16-fix-make-admin-and-protect-global-admin.md`, `2-20-demote-admin-to-member.md`,
  `13-1-global-admin-management-screen.md`, `16-1-manager-role-and-management-view-access.md`
- Depends on: `18-1-claim-group-to-role-mapping-configuration.md`, `18-2-apply-mappings-on-login.md`, Epic 17
- Note: **Epic 18 depends on Epic 17 shipping.**

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
