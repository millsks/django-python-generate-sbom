---
baseline_commit: 4ba7899
---

# Story 21.8: Global Administration Page

Status: review

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

- [x] **Task 1 — List view (AC: #1, #2)** — Global-admin gated.
- [x] **Task 2 — Grant / revoke (AC: #1, #3, #4)** — POST + confirm; last-admin guard in the service.
- [x] **Task 3 — Tests + gate (AC: #5)**.

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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **574 passed**, coverage **96.13%**; frontend **223 passed**.
- `mypy src` clean over 90 files; `ruff check .` clean.
- **22 new tests** in `tests/unit/test_global_admin_pages.py`.
- Routes: `ui-global-admins` → `/platform/global-admins`, `ui-global-admin-grant` →
  `/platform/global-admins/grant`, `ui-global-admin-revoke` → `/platform/global-admins/revoke`.
- **Denial matrix** — for all three URLs: anonymous → **302 → /login**; plain member → **403**;
  org admin → **403**. Every case additionally asserts no tier member's email appears in the
  body the caller lands on.
- Guards: last global admin self-revoke → refused, flag unchanged; self-revoke with another
  admin present → **allowed**, and the page then 403s for them; revoking a non-tier user →
  "not a global admin"; granting an unregistered email → refused.
- Mutations: **405** on GET, **403** without a CSRF token.

### Completion Notes List

**The denial tests assert the body, not just the status — as the story's testing standard
requires.** A 403 that still rendered the roster would leak the entire platform-admin list to
anyone who typed the URL, and the status code alone would not notice. Every global admin in the
module carries a `platform-admin` marker in their address, so each denial asserts that marker is
absent from the response.

**One of those assertions was initially vacuous, and I fixed it.** The anonymous case checks a
**302**, whose body is empty — so "no admin email in the body" was trivially true and tested
nothing. It now follows the redirect and checks the page the caller actually lands on.

**The mixin is the control, and there is a test that says so.** Story 2.17 exists because
admin-only pages were once enforced in the navigation alone. `test_an_org_admin_is_forbidden...`
uses a genuinely privileged principal — an admin, of a normal org — and
`test_an_org_admin_cannot_grant_themselves_the_flag` covers the specific escalation this page
must never permit.

**The Dev Notes' two warnings are both covered by name.**
1. *"Self-revocation by a non-last global admin should be permitted; only the last one is
   blocked."* — Both directions tested. The last one is refused by `LastGlobalAdminError` inside
   the service; nothing in the view re-implements that check. After a permitted self-revoke the
   page correctly 403s for them, which is a nice demonstration that the gate is evaluated per
   request rather than cached.
2. *"The ADMIN org is not a workspace (Story 2.18) — do not let this page become reachable by
   switching into it."* — `test_switching_into_the_admin_org_does_not_open_the_page` pins the
   session's `active_org_id` to the ADMIN org as a plain member and still gets 403.
   `GlobalAdminRequiredMixin` tests membership of the ADMIN org directly and never consults the
   active org, so switching is not a route in.

**The page is deliberately not org-scoped.** It uses `GlobalAdminRequiredMixin`, which requires
no active org — the same 21.4 decision that keeps the platform tier reachable by a global admin
whose only membership is the ADMIN org (and who therefore has no working org at all). An
org-scoped gate here would lock the tier out of its own management page.

**Revocation's side effect is asserted, not just its primary effect.** `revoke_global_admin` also
demotes the person to `member` in every non-admin org — the decided Story 13.1 semantics, since
leaving them an admin of every org they were auto-provisioned into would only half-revoke the
access. `test_revoking_also_demotes_them_in_normal_orgs` checks the role actually changed.

**Grant has no auto-create, matching the add-existing-member flow (Story 2.7).** An unknown email
is an error. Creating an account *and* handing it the highest privilege in the system in one
unreviewed step is precisely what that refusal prevents, and the test says so.

**Revoking a non-tier user reports plainly rather than pretending.** Unlike the cross-org cases
elsewhere in this epic, there is nothing to conceal here: the caller is already a global admin
and can see the whole tier, so "that user is not a global admin" leaks nothing they do not
already know. The target is resolved *from the tier itself*, so this endpoint can only ever act
on an existing global admin.

**Not done here.** There is no audit log of grants and revokes beyond the existing structlog
lines, and no bulk operations — neither exists in the API, and inventing them would put the HTML
path ahead of the contract.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (2)**
- `src/django_apps/inventory/templates/inventory/platform/global_admins.html`
- `tests/unit/test_global_admin_pages.py` (22 tests)

**Modified (5)**
- `src/django_apps/inventory/users/forms.py` — `GrantGlobalAdminForm`
- `src/django_apps/inventory/users/pages.py` — `GlobalAdminsView`, `GlobalAdminGrantView`,
  `GlobalAdminRevokeView`, `_global_admins_context`
- `src/django_apps/inventory/urls_pages.py` — three `ui-` routes
- `src/config/urls.py` — free `platform/` from the SPA catch-all
- `src/django_service/templates/_nav.html` — reverse `ui-global-admins`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Converted the global-admin management screen to a server-rendered page gated by `GlobalAdminRequiredMixin`, with grant-by-email and confirmed revoke as CSRF-protected POSTs calling the existing services. The tier can never be emptied (the last admin's self-revoke is refused by the service), while self-revocation is permitted when someone else remains. 22 tests including a denial matrix that asserts both the status code and that no administrator's email appears in the body the caller lands on, plus a test that switching into the ADMIN org is not a way in. `pixi run ci` exit 0; 574 backend tests at 96.13%. |
