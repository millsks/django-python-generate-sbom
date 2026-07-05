# Story 2.20: Admin Can Demote Another Admin to Member (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an org admin,
I want to demote another admin back to a member without removing them from the org,
so that I can correct an over-promotion without kicking the person out.

## Acceptance Criteria

1. **Per-org demote service + endpoint.** A new `demote_admin_to_member(org, target)` sets that org's `OrgMembership(org, target).role = MEMBER` — for that org only, with no effect on the target's membership in any other org. Exposed as an admin-gated `POST /api/v1/orgs/demote-admin/` with `{user_id}`, returning **204** (mirrors `promote-admin/`, Story 2.16). Raises `NotAMemberError` if the target is not a member of the org.
2. **Guards.** Raise `LastAdminError` if the target is the org's last/sole admin — an org must keep ≥1 admin. Raise `GlobalAdminError` if the target is a global admin — global admins must remain admins of every org (Stories 2.8/2.9). Both surface as the standard 400 membership-error envelope (`_membership_error` → `{error, code}`), and the UI shows a clear, distinct message for each.
3. **Frontend action.** `MembersPage` adds a "Make member" (demote) action on `admin`-role rows, beside "Remove" (the inverse of "Make admin", which shows on non-admin rows). It calls the demote endpoint via a new `demoteAdmin(userId)` in `api/orgs.ts`. Distinct error copy for the last-admin case ("The organization must keep at least one admin.") and the global-admin case ("Global admins can't be demoted.").
4. **Specific membership-error messaging on the Members page.** Every membership action — remove, promote, and demote — surfaces the backend's specific error `code`/message instead of a generic "Could not …". `handleRemove` and `handlePromote` currently catch bare and set a generic string, swallowing the code the backend already returns. Map each `ApiError.code` to a clear, action-appropriate message across all three handlers: `global_admin_protected` → "This user is a global admin and can't be removed from a single org — revoke their global-admin status first." (and the demote-equivalent wording); `last_admin` → "The organization must keep at least one admin."; `admin_org_protected` → the ADMIN-org-protected reason; `not_a_member` → "That user is no longer a member of this org."; `no_such_user` → the existing add-member copy. Fall back to the backend's message (`err.message`) — never a bare "Could not …" — when the code is unmapped. (`handleAdd` already does this code-specific mapping; extend the same pattern to remove/promote/demote.)

5. **Tested.** Promote→demote round-trip returns the row to `member`; demoting the last admin is blocked (`LastAdminError`); demoting a global admin is blocked (`GlobalAdminError`); per-org only (a user who is admin of two orgs keeps their role in the other org); non-admin caller → 403; the frontend "Make member" calls `demoteAdmin`. A `global_admin_protected` **remove** and a `global_admin_protected` **demote** each render the specific reason (not a generic message); a `last_admin` demote renders its specific reason.

## Tasks / Subtasks

- [ ] **Task 1 — Backend demote service (AC: #1, #2)**
  - [ ] `backend/generate_sbom/users/services.py`: add `demote_admin_to_member(org, target)`. Look up the target's membership in `org` (`NotAMemberError` if absent). Guard: `GlobalAdminError` if `is_global_admin(target)`; `LastAdminError` if the target is the sole admin (`_is_sole_admin(org, target)`). Otherwise set `role = OrgMembership.Role.MEMBER` and save. Idempotent-ish: a target who is already a member and not the last admin is a no-op-safe set (they're just not an admin to demote — acceptable to leave as member). Reuse the existing `LastAdminError`, `GlobalAdminError`, `NotAMemberError`, and `_is_sole_admin` helpers.
- [ ] **Task 2 — Backend endpoint + url + serializer (AC: #1, #2)**
  - [ ] `views.py`: add `DemoteAdminView` (admin-gated via `get_admin_org`, `POST`, `UserIdSerializer`, returns 204; `except MembershipError as exc: return _membership_error(exc)`), mirroring `PromoteAdminView`.
  - [ ] `urls.py`: `path("orgs/demote-admin/", DemoteAdminView.as_view(), name="org-demote-admin")`.
- [ ] **Task 3 — Frontend wiring (AC: #3)**
  - [ ] `frontend/src/api/orgs.ts`: add `demoteAdmin(userId)` → `POST /orgs/demote-admin/` (mirror `promoteAdmin`).
  - [ ] `frontend/src/pages/MembersPage.tsx`: on `admin`-role rows, render a "Make member" button beside "Remove"; wire `handleDemote(userId)` → `demoteAdmin`.
- [ ] **Task 4 — Specific membership-error messaging across all actions (AC: #4)**
  - [ ] `frontend/src/pages/MembersPage.tsx`: replace the bare `catch { setError('Could not remove member.') }` in `handleRemove` (MembersPage.tsx:77-78) and `catch { setError('Could not make admin.') }` in `handlePromote` (MembersPage.tsx:87-88) — and the new `handleDemote` — with `catch (err)` blocks that inspect `err instanceof ApiError` and map `err.code`. Factor a shared helper (e.g. `membershipErrorMessage(err, fallback)`) that maps `global_admin_protected`, `last_admin`, `admin_org_protected`, `not_a_member`, `no_such_user` to specific copy and otherwise returns `err.message` (never a bare "Could not …"). Reuse it in `handleAdd`, `handleRemove`, `handlePromote`, and `handleDemote`. Error codes are the `code` class attributes on the `MembershipError` subclasses (`services.py:96-162`), delivered by the `_membership_error` envelope (`views.py:60-62`) and read off `ApiError.code` by the SPA client.
- [ ] **Task 5 — Tests (AC: #5)**
  - [ ] Backend: promote-then-demote returns role to `member`; last-admin demote raises `LastAdminError` / endpoint 400 with that code; global-admin demote raises `GlobalAdminError` / 400; a two-org admin demoted in org A keeps `admin` in org B; endpoint 403 for a non-admin caller.
  - [ ] Frontend: "Make member" calls `demoteAdmin`; a `global_admin_protected` **remove** and a `global_admin_protected` **demote** each show the specific global-admin reason (asserting the generic "Could not …" text is NOT shown); a `last_admin` demote shows its specific reason; the shared mapping falls back to `err.message` for an unmapped code.

## Dev Notes

### Root cause

The Members page only offers "Remove" and (on non-admin rows) "Make admin" (`MembersPage.tsx:132-137`). There is no way to drop an admin back to `member` while keeping them in the org: "Make admin" (Story 2.16, `promote_member_to_admin`) promotes, but there is no inverse service or endpoint. Demotion existed only inside the removed `transfer_admin` (Story 2.16) and was never a standalone, guarded operation.

Separately, the Members page swallows the backend's specific error reason on membership actions: `handleRemove` (`MembersPage.tsx:77-78`) and `handlePromote` (`MembersPage.tsx:87-88`) `catch` bare and set a generic "Could not remove member." / "Could not make admin.", discarding the `code` the backend already returns. So a remove/demote blocked by `global_admin_protected` (a global admin can't be dropped from a single org), `last_admin`, or `admin_org_protected` shows an unhelpful generic message instead of the actionable reason. `handleAdd` (`MembersPage.tsx:59-67`) already maps codes to specific copy — the fix extends that pattern to every membership action.

### Design

- Mirror `promote_member_to_admin` / `PromoteAdminView` / `promoteAdmin` exactly — same admin gate, same 204, same `UserIdSerializer`, same `_membership_error` envelope — so promote and demote are symmetric.
- Guards reuse the invariants already enforced on removal: `_guard_membership_removal` already raises `GlobalAdminError` and `LastAdminError` (services.py:205-227); demote enforces the same two so it can't strip the last admin or a global admin.

### Notes

- Pairs with **Story 2.16** (promote) — together they are the promote↔demote pair on the Members page.
- Overlaps **Story 13.1** (global-admin management screen), which also touches `MembersPage` and the users backend. Implement **after 13.1 merges** to avoid churn.

### References

- `backend/generate_sbom/users/services.py` (`promote_member_to_admin` to mirror; `LastAdminError`, `GlobalAdminError`, `NotAMemberError`, `_is_sole_admin`, `is_global_admin`, `_guard_membership_removal`)
- `backend/generate_sbom/users/views.py` (`PromoteAdminView`, `_membership_error`, `UserIdSerializer`), `urls.py` (`orgs/promote-admin/`)
- `frontend/src/api/orgs.ts` (`promoteAdmin` to mirror), `frontend/src/pages/MembersPage.tsx` (`handleAdd` code-mapping to reuse; `handlePromote`/`handleRemove` bare catches to fix; the row actions)
- Error codes: `MembershipError` subclasses' `code` attributes (`backend/generate_sbom/users/services.py:96-162` — `last_admin`, `global_admin_protected`, `admin_org_protected`, `not_a_member`, `no_such_user`), `_membership_error` envelope (`backend/generate_sbom/users/views.py:60-62`), read off `ApiError.code` client-side
- Related: `2-16-fix-make-admin-and-protect-global-admin.md`, `2-8-global-admin-org-and-cross-org-provisioning.md`, `2-9-membership-edge-cases.md`, `13-1-global-admin-management-screen.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
