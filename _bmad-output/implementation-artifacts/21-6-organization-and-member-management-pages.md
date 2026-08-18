---
baseline_commit: 9d7074f
---

# Story 21.6: Organization and Member Management Pages

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.5**. Admin-gated by the `OrgAdminRequiredMixin` from Story 21.4.

## Story

As an org admin,
I want to manage my organisation and its members through server-rendered pages,
so that I can add, remove, and re-role members without the SPA.

## Acceptance Criteria

1. **The organisation hub is converted.**
   Given `OrganizationPage.tsx` is an admin-facing hub that links to members, API keys, and org creation
   rather than duplicating their logic (Story 2.11), when it is converted, then an admin-gated page presents
   the same destinations with the same composition-by-linking approach.
2. **Org creation is global-admin only.**
   Given Story 2.12 deliberately reversed self-service org creation and restricted it to **global** admins,
   when `CreateOrgDialog.tsx` is converted, then org creation is a crispy form gated by the
   `GlobalAdminRequiredMixin`, the affordance is **hidden** for non-global-admins, and the creating flow makes
   the intended admin the new org's admin.
3. **Member management actions are converted.**
   Given `MembersPage.tsx` supports adding an **existing** user by email (Story 2.7), creating a **new** user
   account on their behalf (Story 2.10), removing a member (FR-1.4), and promoting/demoting admin (Stories
   2.16, 2.20), when it is converted, then each action is a CSRF-protected POST calling the existing member
   services directly, and destructive actions require confirmation.
4. **New-member credentials are shown once.**
   Given an admin creates an account on a member's behalf and shares the credentials out-of-band (FR-1.3, no
   email infrastructure), when the account is created, then the temporary password is displayed **once** on
   the result page with an explicit "share out-of-band, it will not be shown again" warning, and it is not
   written to the session or any log.
5. **The last admin is protected.**
   Given an org must always retain at least one admin (FR-1.5) and Story 2.16 additionally protects global
   admins from demotion, when the last admin attempts self-demotion or removal, then the server rejects it
   with a form error and the membership is unchanged.
6. **Leaving an org does not delete it.**
   Given a non-owner member can leave an org (FR-1.7), when they do so, then the org survives, their access
   ends immediately, and they land on the zero-org state if it was their only membership.
7. **Gate green with authorisation coverage.**
   When the story completes, then tests cover add-existing, create-new, remove, promote, demote, last-admin
   protection, leave-org, non-admin denial, and cross-org denial, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [x] **Task 1 — Organisation hub page (AC: #1)** — Admin-gated; links only.
- [x] **Task 2 — Create-org form (AC: #2)** — Global-admin gated; affordance hidden otherwise.
- [x] **Task 3 — Members list + add-existing + create-new (AC: #3, #4)** — Two distinct flows; one-time
  credential reveal for create-new.
- [x] **Task 4 — Remove / promote / demote (AC: #3, #5)** — POST + confirm; last-admin and global-admin guards
  enforced in the service, not the template.
- [x] **Task 5 — Leave org (AC: #6)**.
- [x] **Task 6 — Tests + gate (AC: #7)**.

## Dev Notes

### Grounded facts (verified)

- Endpoints already present in `generate_sbom/users/urls.py`: `orgs/create/`, `orgs/members/`,
  `orgs/members/create-user/`, `orgs/members/<int:user_id>/`, `orgs/promote-admin/`, `orgs/demote-admin/`,
  `orgs/leave/`, `orgs/`, `orgs/me/`.
- `frontend/src/pages/OrganizationPage.tsx` header comment (Story 2.11): "one admin-facing place that gathers
  the org-administration destinations … It composes the existing management pages by linking to them rather
  than duplicating their logic." Preserve that.
- `frontend/src/pages/MembersPage.tsx` uses a `ToggleButtonGroup` for the member/admin role control.
- Prior stories: 2.3 (org administration), 2.5 (create org from UI), 2.7 (add/remove **existing** users by
  email), 2.8 (global-admin org + cross-org provisioning), 2.9 (membership edge cases), 2.10 (admin creates a
  **new** user account), 2.11 (org hub), 2.12 (**org creation restricted to global admins**), 2.16 (fix
  make-admin: promote, don't transfer; protect global admins), 2.20 (demote admin to member).

### Two distinct member flows — do not merge them

Story 2.7 adds an **existing** user by email; Story 2.10 creates a **new** account on the member's behalf.
They were separated deliberately (2.7 originally raised `no_such_user`, and 2.10 was reopened to restore
provisioning). Keep them as two form actions with distinct outcomes.

### Watch for

- **Promote ≠ transfer.** Story 2.16 fixed a bug where "Make admin" transferred rather than promoted. The
  service already encodes the correct behaviour — call it, do not reimplement.
- **Global admins are protected from demotion** (2.16).
- **`is_admin` is per-active-org** — an admin of org A managing org B's members must be refused.

### Testing standards

- Authorisation matrix per action: member, org admin, global admin, cross-org.
- A test asserting the temporary password appears exactly once and is absent from a subsequent page render.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.6: Organization and Member Management Pages]
- `frontend/src/pages/{OrganizationPage,MembersPage}.tsx`, `frontend/src/components/CreateOrgDialog.tsx`,
  `generate_sbom/users/{views,services,selectors}.py`.
- Upstream: `21-5-authentication-pages.md`.
- Architecture: AD-2 (org isolation), AD-14 (org/admin/auth model).

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **534 passed**, coverage **96.05%**; frontend **223 passed**.
- `mypy src` clean over 90 files; `ruff check .` clean; `manage.py check` clean.
- **35 new tests** in `tests/unit/test_org_pages.py`.
- Route resolution — `ui-organization` → `/organization`, `ui-org-create` →
  `/organization/create`, `ui-org-leave` → `/organization/leave`, `ui-members` → `/members`,
  and `ui-member-{add,create,remove,promote,demote}` → `/members/*`.
- Authorization matrix: every one of the five member mutations returns **403** for a plain
  member, **302 → /login** for anonymous, **405** on GET, and **403** without a CSRF token.
- **Live server walkthrough** (seeded global admin, whose only membership is the ADMIN org):
  - `/organization` → the **no-org state**, because Story 2.18 makes the ADMIN org never
    resolve as a working org — while `/organization/create` stays **reachable**, which is
    exactly the Story 21.4 split (`GlobalAdminRequiredMixin` requires no org) working in the
    real world rather than only in tests.
  - Created "Live Check Org" through the real form → 302, hub then renders it.
  - Provisioned a member through the real form → the reveal page showed the temporary
    password and the "will not be shown again" warning; a subsequent `/members` render
    contained it **0 times**.
  - `/keys` and `/upload` still served by the **SPA**.

### Completion Notes List

**A real bug my own tests caught: the invalid-form path returned 405.** Both add-member views
originally re-rendered by dispatching at the roster view — `MembersView.as_view()(request, ...)`
— but `MembersView` is a `TemplateView`, which permits only GET/HEAD/OPTIONS. So *any*
validation error (unregistered email, already-a-member, email-taken) produced
**405 Method Not Allowed** instead of the form with its error. Extracted `_members_context()`
and now `render()` the template directly, so the redisplayed page carries the same roster as a
fresh one. This is the kind of failure that only shows up on the unhappy path, which is why
three of the four initial failures were error-path tests.

**One-time credential reveal is a render, not a redirect (AC #4).** `MemberCreateUserView`
renders `member_created.html` straight from the POST. A redirect would have to carry the
password through the session or the query string, and AC #4 names the session explicitly.
Rendering keeps it in that single response: not in the session (asserted), not on any later
page (asserted), and not in a log — `create_member_user`'s own docstring commits to that.
The trade-off, stated plainly: a browser refresh re-posts the form rather than re-revealing,
which is the correct failure mode for a secret.

**Every invariant is delegated, never re-implemented.** Last-admin, global-admin protection,
ADMIN-org protection and promote-is-not-transfer all live in the services already. The views
catch `MembershipError` and surface `exc.message`; they contain no membership logic of their
own. Re-implementing a guard in a view would give the HTML path different rules from the API
path — precisely the drift Story 2.9 and AD-2 exist to prevent. The tests assert the *pages*
route through those guards (last admin cannot be demoted or removed, a global admin cannot be
demoted, promote leaves the promoter an admin — the bug Story 2.16 fixed).

**Cross-org safety comes from the lookup, not a check.** `_MemberActionView._target()` resolves
the target through `OrgMembership.objects.filter(org=self.org, user_id=...)`, so an admin of
org A posting a member id from org B simply finds nothing and gets "not a member of this org".
There is no branch that could be got wrong, and `test_an_admin_of_another_org_cannot_touch_this_orgs_members`
pins it with a genuinely privileged outsider (an admin — of somewhere else).

**The two add-member flows are kept apart deliberately.** Story 2.7 (add existing) refuses an
unregistered email rather than auto-creating; Story 2.10 (create new) refuses an email that
already exists and points the admin at the other flow. Two forms, two endpoints, two error
messages — merging them would recreate the bug both stories were reopened to fix. Tested from
both directions.

**Org creation is global-admin only, enforced twice over.** The affordance is hidden on the hub
for non-global-admins *and* `CreateOrgView` is gated by `GlobalAdminRequiredMixin`, so an org
admin who types the URL gets 403 rather than a form. Story 2.12 deliberately reversed
self-service creation, so "org admin" is explicitly not enough — asserted directly. On success
the new org is made active, so the creator lands in the thing they just made.

**Leaving clears the session's pinned org.** `leave_org` deletes the membership, but the session
still names the org just left; without popping `SESSION_ACTIVE_ORG` the next request would try
to resolve an org the user no longer belongs to. Cleared explicitly so access ends immediately
(AC #6), and the org itself survives — both asserted.

**Nav now reverses named URLs for the converted pages.** `_nav.html` resolves
`{% url 'ui-members' %}` / `{% url 'ui-organization' %}` into variables at the top of the
template, because `{% include %}` cannot take a `{% url %}` expression as an argument. The
unconverted destinations remain literal paths until their stories land.

**Presentation vs enforcement is stated in the template.** The roster hides the role and remove
controls on the caller's own row, and `members.html` says in a comment that this is presentation
only. Every guard is server-side; the sole-admin tests post directly and are refused.

**Not done here.** `/keys` is Story 21.7 and still points at the SPA. There is no bulk member
import, no invitation email (there is no email infrastructure at all — FR-1.3), and no
role-change confirmation dialog (only the destructive remove and leave actions confirm).

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability
violations.

### File List

**New (5)**
- `src/django_apps/inventory/templates/inventory/orgs/hub.html` — the link-only admin hub
- `src/django_apps/inventory/templates/inventory/orgs/create.html` — global-admin-gated org creation
- `src/django_apps/inventory/templates/inventory/orgs/members.html` — roster + both add forms
- `src/django_apps/inventory/templates/inventory/orgs/member_created.html` — one-time reveal
- `tests/unit/test_org_pages.py` (35 tests)

**Modified (5)**
- `src/django_apps/inventory/users/forms.py` — `CreateOrgForm`, `AddExistingMemberForm`,
  `CreateMemberUserForm`
- `src/django_apps/inventory/users/pages.py` — `OrganizationHubView`, `CreateOrgView`,
  `MembersView`, `MemberAddExistingView`, `MemberCreateUserView`, `MemberRemoveView`,
  `MemberPromoteView`, `MemberDemoteView`, `LeaveOrgView`, `_members_context`
- `src/django_apps/inventory/urls_pages.py` — nine `ui-` routes
- `src/config/urls.py` — free `organization` and `members` from the SPA catch-all
- `src/django_service/templates/_nav.html` — reverse the two converted destinations
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Converted the organisation hub, org creation, and member management to server-rendered pages. The hub composes by linking (Story 2.11); org creation is global-admin only (Story 2.12), gated server-side and hidden in the UI. The two add-member flows stay distinct (add-existing vs create-new), and a provisioned account's temporary password is revealed exactly once on a rendered result page — never via session, redirect, or log. Every mutation is a CSRF-protected POST delegating its invariants to the existing services, with cross-org safety coming from an org-scoped target lookup. 35 tests covering the authorization matrix and every guard. `pixi run ci` exit 0; 534 backend tests at 96.05%. |
