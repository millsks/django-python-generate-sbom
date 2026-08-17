# Story 21.8: Global Administration Page

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.7**. Gated by the `GlobalAdminRequiredMixin` from Story 21.4.

## Story

As a global administrator,
I want to manage global admins through a server-rendered page,
so that platform administration survives the SPA removal.

## Acceptance Criteria

1. **The global-admins page is converted.**
   Given `GlobalAdminsPage.tsx` is gated by `GlobalAdminRoute` and backed by `/admin/global-admins/`, when it
   is converted, then the page is gated by the global-admin mixin, lists current global admins, and grants or
   revokes the flag via CSRF-protected POSTs calling the existing services directly.
2. **Non-global-admins cannot reach it by URL.**
   Given global admin is the highest privilege in the system (Story 13.1, **AD-14**), when an anonymous user,
   an org member, or an org admin requests the page by URL, then they receive **403** and the page contents
   never render — the nav item being hidden is not the control.
3. **The platform cannot be left without an administrator.**
   Given at least one global admin must always exist, when the last global admin attempts to revoke their own
   flag, then the server rejects it with a form error and the flag is unchanged.
4. **Destructive changes are confirmed.**
   Given revoking global admin is a privilege change, when a revoke is requested, then a confirmation step
   precedes it.
5. **Gate green with a full denial matrix.**
   When the story completes, then tests cover grant, revoke, last-admin protection, and denial for anonymous,
   member, and org-admin principals, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — List view (AC: #1, #2)** — Global-admin gated.
- [ ] **Task 2 — Grant / revoke (AC: #1, #3, #4)** — POST + confirm; last-admin guard in the service.
- [ ] **Task 3 — Tests + gate (AC: #5)**.

## Dev Notes

### Grounded facts (verified)

- `generate_sbom/users/urls.py` — `admin/global-admins/` and `admin/global-admins/<int:user_id>/`.
- `frontend/src/api/auth.ts` — `CurrentUser.is_global_admin` was added by Story 2.12 and is described as the
  SPA's source of truth for gating; the server-side mixin replaces it.
- Story 13.1 delivered the global-admin management screen; Story 2.8 established the global-admin ADMIN org;
  Story 2.12 restricted org creation to global admins; Story 2.16 protects global admins from demotion via the
  org-level member controls.
- `base.py:38-41` + `users/models.py` — `Org.is_admin_org` (migration `0003_org_is_admin_org`,
  seeded by `0004_seed_admin_org`) backs the global-admin tier.

### Privilege escalation is the risk here

This page grants the highest privilege in the system. The mixin — not the hidden nav item — is the control, and
AC #2 tests exactly that. Note that Story 2.17 exists because admin-only pages were previously enforced only in
the nav; do not repeat that mistake at the global tier.

### Watch for

- **Self-revocation** by a non-last global admin should be permitted; only the *last* one is blocked.
- **The ADMIN org is not a workspace** (Story 2.18) — do not let this page become reachable by switching into
  it.

### Testing standards

- Denial tests must assert both the status code **and** that no admin email appears in the response body.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.8: Global Administration Page]
- `frontend/src/pages/GlobalAdminsPage.tsx`, `frontend/src/components/GlobalAdminRoute.tsx`,
  `generate_sbom/users/{views,services,models}.py`.
- Upstream: `21-7-api-key-management-page.md`.
- Architecture: AD-14 (org/admin/auth model).

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
