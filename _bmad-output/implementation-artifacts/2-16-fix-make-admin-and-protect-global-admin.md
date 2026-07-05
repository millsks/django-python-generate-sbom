# Story 2.16: Fix "Make admin" — Promote, Don't Transfer; Protect Global Admins (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an org admin,
I want "Make admin" to add another admin without demoting anyone,
so that I don't accidentally strip my own (or the global admin's) admin rights.

## Acceptance Criteria

1. **Promote, don't transfer.** "Make admin" promotes the target to admin of that org and demotes no one — an org may have many admins. Backend `promote_member_to_admin(org, target)` sets only `OrgMembership(org, target).role = ADMIN` (raises `NotAMemberError` if not a member; idempotent if already admin).
2. **Per-org only.** Promotion is strictly scoped to the one org: it does NOT call `grant_global_admin`, add the target to the ADMIN org, or touch their membership in any other org. A promoted member is an admin of that org only — not a global admin.
3. **Global admins can't be demoted.** The buggy `transfer_admin` (promote target + demote the sole-admin caller) is removed — it was the only demotion path and could strip a global admin, violating Story 2.8. No code path drops a global admin below admin.
4. **Correct endpoint + no false error.** New `POST /api/v1/orgs/promote-admin/` (admin-gated) returns **204** (the old transfer returned 200 with an empty body, which the SPA's `apiRequest` — only special-casing 204 — turned into a spurious "Could not transfer admin." even though the change committed).
5. **Tested.** Promote adds an admin without demoting; per-org (`is_global_admin` stays false, other-org role unchanged); non-admin caller → 403; non-member → 400; the frontend "Make admin" calls the promote endpoint.

## Tasks / Subtasks

- [ ] **Task 1 — Backend promote service + endpoint (AC: #1, #2, #4)**
  - [ ] `services.promote_member_to_admin(org, target)` — set that org's membership role to ADMIN only; no demotion, no `grant_global_admin`, no other-org writes. Remove `transfer_admin`.
  - [ ] `PromoteAdminView` (`POST /orgs/promote-admin/`, admin-gated via `get_admin_org`) → 204. Remove `TransferAdminView` + `/orgs/transfer-admin/`. Rename `TransferAdminSerializer` → `UserIdSerializer` (reused by `GrantGlobalAdminView`).
- [ ] **Task 2 — Frontend wiring (AC: #1, #4)**
  - [ ] `api/orgs.ts`: replace `transferAdmin` with `promoteAdmin(userId)` → `POST /orgs/promote-admin/`. `MembersPage` "Make admin" → `handlePromote` → `promoteAdmin`; error copy "Could not make admin."
- [ ] **Task 3 — Tests (AC: #5)**
  - [ ] Backend: promote adds admin without demoting the caller; `is_global_admin(target)` stays false and their role in a second org is unchanged; endpoint 403 for non-admin, 400 for non-member; promote-then-leave lets a sole admin exit. Frontend: "Make admin" calls `promoteAdmin`.

## Dev Notes

### Root cause

`transfer_admin` (Story 2.3, FR-1.5) promoted the target AND demoted the caller when `_is_sole_admin(caller)`. Wired to the "Make admin" button, it silently demoted the sole admin — and when that caller was the seeded global admin, it stripped their admin rights (`get_admin_org` reads the stored role), leaving a non-admin promoted and the global admin a mere member. It was also non-atomic and returned 200 with an empty body, so `apiRequest` (`client.ts`, only handles 204) threw on the empty JSON → the false "Could not transfer admin." while the DB change committed.

### Operational repair for already-corrupted data (manual, not code)

If a global admin was already demoted by the old bug, restore them:

```
docker compose exec web pixi run python backend/manage.py bootstrap_admin_org
```

`bootstrap_admin_org` re-runs `grant_global_admin` for every superuser (`update_or_create(role=admin)` across all orgs), restoring demoted global admins to admin everywhere.

### References

- `backend/generate_sbom/users/services.py` (`promote_member_to_admin`), `views.py` (`PromoteAdminView`, `AuthMeView`), `urls.py`, `serializers.py` (`UserIdSerializer`)
- `frontend/src/api/orgs.ts` (`promoteAdmin`), `frontend/src/pages/MembersPage.tsx`
- Related: `2-3-org-administration-and-membership-management.md`, `2-8-global-admin-org-and-cross-org-provisioning.md`, `2-17-admin-route-and-api-authorization.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
