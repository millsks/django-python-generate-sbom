# Story 18.1: Claim/Group → Role Mapping Configuration

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **First story of Epic 18 (Phase 2) — build it first. DEPENDS ON EPIC 17 SHIPPING.** Phase 2 maps IdP
> **groups/claims → entitlements** (org membership + roles). This story defines and validates the operator-
> configured **mapping** only; Story 18.2 applies it at login; Story 18.3 defines precedence/reconciliation.
> Nothing here changes any user's memberships yet.

## Story

As an operator,
I want to configure how IdP groups/claims map to org memberships and roles,
so that Phase 2 can provision and sync a user's entitlements from their IdP identity instead of managing every
role by hand.

## Acceptance Criteria

1. **Mapping schema.**
   Given the IdP emits group/role claims (e.g. `groups`, a roles claim, or a custom claim), when the operator
   configures Phase 2, then there is a well-defined mapping from a **claim value** (group name / claim string)
   to an **entitlement**: an `(org, role)` pair where role ∈ {member, manager, admin} and, for the platform
   tier, an optional **global-admin** grant. The mapping's shape, source (settings/env/DB — operator-
   documented), and precedence order are specified.
2. **Roles are the existing app roles.**
   Given the app's role model, when mappings target a role, then they use the **existing** roles only —
   member / manager (Story 16.1) / admin (Story 2.3/2.16) / global-admin (Story 2.8/13.1). Phase 2 introduces
   no new role; it only *sources* the existing ones from claims.
3. **Which claim(s) to read.**
   Given the IdP claims are captured by Phase 1 in allauth's **`SocialAccount.extra_data`** (and available via
   the adapter hooks), when the mapping is defined, then the operator specifies **which claim** (key in
   `extra_data` — e.g. `groups`, a roles claim) carries the groups/roles and how multi-valued claims are
   handled (a user in several groups can map to several entitlements). Absent/empty claim → no IdP-derived
   entitlements (the user's app-managed state is untouched — reconciliation detail is Story 18.3).
4. **Validation, no application.**
   Given a configured mapping, when the app loads it, then it is **validated** (well-formed; referenced orgs
   exist or are resolvable; roles are valid; no contradictory duplicate targets) and validation errors are
   raised/logged (structlog, specific exceptions) — but **this story does not apply the mapping to any user**
   (that is Story 18.2). A dry-run/preview that, given a sample claim set, reports the entitlements it *would*
   produce is provided for operator verification.
5. **Invariant awareness declared.**
   Given the guarded invariants (last-admin / last-global-admin protections from Stories 2.9/2.16/13.1), when
   the mapping schema is defined, then it documents that **application** of mappings (Story 18.2) and
   **reconciliation** (Story 18.3) must preserve those invariants — the mapping config itself cannot express a
   state that would later be allowed to violate them.
6. **Tested; CI green.**
   Backend tests cover: a valid mapping loads; malformed/contradictory mappings are rejected with clear errors;
   the dry-run preview turns a sample claim set into the expected `(org, role)` entitlements (incl.
   multi-valued claims and the absent-claim case); no user membership is written by this story. `pixi run ci`
   green.

## Tasks / Subtasks

- [ ] **Task 1 — Mapping schema + source (AC: #1, #2, #3)** — define the claim→`(org, role)`/global-admin
  mapping structure and its configuration source; document which claim(s) are read + multi-value handling.
- [ ] **Task 2 — Loader + validation (AC: #4, #5)** — load + validate the mapping (well-formed, orgs/roles
  valid, no contradictions); specific exceptions + structlog; **no** membership writes.
- [ ] **Task 3 — Dry-run preview (AC: #4)** — `preview_entitlements(claims) -> list[(org, role)]` (+ global-
  admin) for operator verification, with no side effects.
- [ ] **Task 4 — Tests (AC: #6)** — see ACs.
- [ ] `pixi run ci` green.

## Dev Notes

### Fixed decisions (product owner)

- **Phase 2 depends on Phase 1.** Epic 18 is sequenced **after Epic 17 ships** — it consumes the validated OIDC
  claims/session Phase 1 establishes, reading the claims from django-allauth's **`SocialAccount.extra_data`**
  (and its adapter hooks).
- **Config first, apply later.** This story defines + validates the mapping and offers a dry-run; it changes
  **no** user's memberships/roles. Application is 18.2; precedence/reconciliation is 18.3.
- **Existing roles only.** Claims source the existing member/manager/admin/global-admin tiers — no new role.
- **Invariants are sacred.** The last-admin / last-global-admin guards must survive Phase 2; the schema is
  designed so 18.2/18.3 can enforce them.

### Current state (verified)

- Roles: `OrgMembership.Role` ADMIN/MEMBER (`backend/generate_sbom/users/models.py:89-94`) + MANAGER
  (Story 16.1); global-admin via the ADMIN org (Story 2.8) / management screen (Story 13.1).
- Guarded invariants: last-admin/edge cases (Story 2.9), protect-global-admin (Story 2.16), global-admin
  management (Story 13.1).
- Validated OIDC claims are available from Phase 1 in allauth's `SocialAccount.extra_data` (Stories 17.2/17.3 —
  the `(iss, sub)` `SocialAccount` + its `extra_data` claims) and via the adapter hooks.

### Testing standards

- Backend: pytest; feed sample claim dicts to the loader + `preview_entitlements`; assert produced
  entitlements and that no `OrgMembership` rows are written.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 18.1: Claim/Group → Role Mapping Configuration]
- `backend/generate_sbom/users/models.py:89-94`, `2-8-global-admin-org-and-cross-org-provisioning.md`,
  `2-9-membership-edge-cases.md`, `2-16-fix-make-admin-and-protect-global-admin.md`,
  `13-1-global-admin-management-screen.md`, `16-1-manager-role-and-management-view-access.md`
- Depends on: Epic 17 (`17-1`…`17-8`, esp. `17-3` claims/identity)
- Downstream: `18-2-apply-mappings-on-login.md`, `18-3-precedence-and-reconciliation.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
