# Story 2.9: Membership Edge Cases

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want membership edge cases handled safely,
so that orgs can't be left in a broken or orphaned state.

## Acceptance Criteria

1. **Last admin protected.** An org's last admin cannot leave or be removed unless another admin (or a global admin) remains — or admin is transferred first (existing `transfer-admin`).
2. **Empty org behavior defined.** When the last member leaves/is removed, the defined behavior applies (documented — delete the org, or leave it admin-owned by global admins), consistently for normal orgs vs the system ADMIN org.
3. **Global admin not strandable.** A global admin (auto-added to every org) isn't accidentally strandable: they can't be the "last admin" that blocks removal (since global admins are always present), and removing them from a single org is handled per the global model (Story 2.8).
4. **Tested + green CI.** The rules are covered by tests and `pixi run ci` is green.

## Tasks / Subtasks

- [ ] **Task 1 — Confirm/extend last-admin protection (AC: #1)**
  - [ ] `_is_sole_admin()` (`backend/generate_sbom/users/services.py:118-121`), `remove_member` (`:141-149`), and `leave_org` (`:165-173`) already raise `LastAdminError` when an op would remove the only admin. Confirm this holds once global admins exist as real admin memberships (a normal admin leaving is allowed when a global admin remains, since they count as an admin).
  - [ ] `transfer_admin` (`:152-162`) is the escape hatch — verify it still lets a sole admin hand off before leaving.
- [ ] **Task 2 — Define + implement empty-org behavior (AC: #2)**
  - [ ] Decide and document the rule for a normal org losing its last member. **Recommended:** because global admins are auto-provisioned into every org (Story 2.8), a normal org is effectively never memberless — leave it admin-owned by the global admins rather than auto-deleting. Handle the genuine edge (no global admins seeded yet) explicitly.
  - [ ] Define distinct behavior for the **ADMIN org**: it must never lose its last global admin (that would destroy the global-admin tier) — block removing/leaving the last member of the ADMIN org.
- [ ] **Task 3 — Global-admin non-stranding (AC: #3)**
  - [ ] Ensure a global admin can't be counted as the blocking "last admin" of a normal org (removing a normal admin succeeds while a global admin remains).
  - [ ] Define removing a global admin from a **single** normal org: either block it (they belong to all orgs by policy) or allow-and-note that re-provisioning may re-add them. Document the choice; keep it consistent with Story 2.8's "admin of ALL orgs" invariant.
- [ ] **Task 4 — Tests (AC: #4)**
  - [ ] Backend (`backend/tests/unit/test_membership.py`): sole admin can't leave/be removed; transfer-then-leave works; a normal admin can leave when a global admin remains; last member of the ADMIN org can't be removed; global admin isn't treated as strandable. Cover both normal-org and ADMIN-org paths.

## Dev Notes

### Most of the primitives already exist — this story hardens the edges

- `_is_sole_admin` / `LastAdminError` (`services.py:64-68, 118-121`) already guard `remove_member` and `leave_org`. The new dimension is the **global-admin interaction** from Story 2.8: global admins are real ADMIN memberships in every org, which changes what "sole admin" means and introduces the ADMIN-org special case.
- `leave_org` view (`views.py:281-294`) pops the session active org on leave — a user who leaves their last org lands in the zero-org state (Story 2.6). No conflict.

### Decisions to make explicit (and document)

1. **Empty normal org:** recommend "not auto-deleted; global admins retain ownership." Document the fallback when no global admins exist yet.
2. **ADMIN org:** never allow it to reach zero global admins; block the last removal/leave.
3. **Removing a global admin from one org:** pick block-vs-allow and state it; must not violate Story 2.8's "global admin is admin of ALL orgs."

Keep these decisions in the story/PR and in developer docs, since they define product behavior, not just code.

### Cross-story dependencies

- **Depends on Story 2.8** (global-admin model + provisioning) and interacts with **Story 2.7** (remove flow) and **Story 2.6** (zero-org landing). Recommended order: implement **last** in Epic 2 (after 2.8).

### Testing standards

- Backend: pytest `@pytest.mark.django_db`, DRF `APIClient` where an endpoint is exercised, service-level tests otherwise; `backend/tests/unit/test_membership.py`. Coverage gate ≥90% via `pixi run cov`.

### Project Structure Notes

- Backend only: `backend/generate_sbom/users/{services,views}.py` and tests. No new frontend. Any doc updates under `docs/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.9: Membership Edge Cases] (lines 645-671)
- Backend: `backend/generate_sbom/users/services.py:118`, `:141`, `:152`, `:165`, `views.py:281`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
