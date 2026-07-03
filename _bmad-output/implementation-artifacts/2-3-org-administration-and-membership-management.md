# Story 2.3: Org Administration & Membership Management

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an org admin,
I want to create orgs, add and remove members, transfer admin rights, and allow users to leave orgs,
so that I can manage my team's access to the service.

## Acceptance Criteria

1. Given I am logged in, when I submit the create-org form with a unique name, then a new `Org` is created and I am added as its admin via a new `OrgMembership` (FR-1.2).
2. Given I am an org admin, when I submit the add-member form with a new member's email and temporary password, then a `User` account is created (or the existing user is found) and an `OrgMembership` with `role="member"` is created; no email is sent (FR-1.3).
3. Given I am an org admin and call `DELETE /api/v1/orgs/{org_id}/members/{user_id}/`, when the request is processed, then the user's `OrgMembership` is deleted immediately and they can no longer access any resource in that org (FR-1.4).
4. Given I am an org admin and transfer admin privileges to another member via the UI, when the transfer completes, then the target member's role is set to `"admin"`; my role is set to `"member"` if I was the only admin (FR-1.5).
5. Given an org with exactly one admin, when that admin attempts to remove themselves, leave the org, or transfer away admin without a replacement, then the action is rejected with error `"An org must always have at least one admin."`.
6. Given I am a non-sole-admin member of an org, when I select "Leave org" in the UI, then my `OrgMembership` is deleted and the org no longer appears in my org switcher (FR-1.7).
7. Given `GET /api/v1/orgs/{org_id}/members/` with a valid API key scoped to that org, when the request is processed, then the response lists all members with name, email, role, and joined date; members from other orgs are not included (AD-2).
8. Given a member (non-admin) views the membership management page, when the page renders, then the add-member form, remove buttons, and transfer-admin controls are not rendered.

## Tasks / Subtasks

- [ ] Task 1 — Create additional org (AC: #1)
  - [ ] Reuse `create_org(name, admin_user)` from `users/services.py` (shared with Story 2.1 registration)
  - [ ] Endpoint creates the `Org` + an admin `OrgMembership` for the caller; unique-name/slug validation
  - [ ] New org appears in the caller's org switcher (Story 2.2)
- [ ] Task 2 — Add member (AC: #2)
  - [ ] `POST /api/v1/orgs/members/` (admin only): `create_member(org, email, temp_password, role="member")` — finds existing user by email or creates a new `User`, then creates an `OrgMembership(role="member")`
  - [ ] No email infrastructure — admin shares credentials out-of-band (FR-1.3). Do NOT add SMTP.
  - [ ] Idempotency: adding an existing member returns a clear error rather than a duplicate (respect `unique_together(org, user)`)
- [ ] Task 3 — Remove member (AC: #3, #5)
  - [ ] `DELETE /api/v1/orgs/{org_id}/members/{user_id}/` (admin only) deletes the `OrgMembership`
  - [ ] Guard the last-admin invariant: removing the sole admin is rejected (AC #5)
  - [ ] Removed member immediately loses access (their membership no longer resolves in `.for_org` checks)
- [ ] Task 4 — Transfer admin (AC: #4, #5)
  - [ ] Set target member's role to `admin`; demote the caller to `member` if they were the only admin
  - [ ] Reject transfer that would leave zero admins (AC #5)
- [ ] Task 5 — Leave org (AC: #6, #5)
  - [ ] A non-sole-admin member deletes their own `OrgMembership`; the org disappears from their switcher
  - [ ] A sole admin cannot leave (AC #5) — must transfer admin first
  - [ ] A user cannot leave/delete their personal org via this path if it would orphan resources — follow FR-1.7 ("leave an org they do not own"); personal-org owners use a different lifecycle (out of scope here)
- [ ] Task 6 — List members (AC: #7)
  - [ ] `GET /api/v1/orgs/members/` (or `/orgs/{org_id}/members/`) returns members with name, email, role, joined date, scoped to the org (AD-2); cross-org returns `404` (API) / `403` (web UI)
  - [ ] `get_org_members(org)` selector backs this
- [ ] Task 7 — Admin-gated UI (AC: #8)
  - [ ] Membership management page renders add/remove/transfer controls ONLY for admins; members see a read-only roster
  - [ ] Enforce authorization on the server too (never rely on UI hiding alone) — non-admin calls to admin endpoints are rejected
- [ ] Task 8 — Tests (AC: all)
  - [ ] Unit: create-org adds caller as admin; add-member creates member + membership, no email sent
  - [ ] Unit: last-admin invariant blocks self-removal, sole-admin leave, and admin-away transfer (exact error string)
  - [ ] Unit: transfer admin promotes target and demotes sole admin
  - [ ] Unit: list members is org-scoped (a member of another org is excluded); non-admin blocked from admin actions
  - [ ] `pixi run cov` ≥90% on membership services/selectors/views

## Dev Notes

### The "at least one admin" invariant (AC #5 — load-bearing)

Three operations can violate it — self-removal, sole-admin leave, and transfer-away-from-sole-admin. Centralize the guard in the service layer (e.g. a `_assert_org_keeps_an_admin(org, ...)` check invoked by remove/leave/transfer) so all three paths enforce the SAME rule and the SAME error string: `"An org must always have at least one admin."` Do not scatter the check across views.

### Services / selectors (solution-design.md §3.1)

```python
# users/services.py
def create_org(name: str, admin_user: User) -> Org: ...        # shared with 2.1
def create_member(org: Org, email: str, temp_password: str, role: str) -> User: ...

# users/selectors.py
def get_org_members(org: Org) -> QuerySet[User]: ...
```

Service functions take `org` first, accept/return plain objects (AD-3). Mutation in `services.py`, reads in `selectors.py`, ORM-only `models.py`.

### No email infrastructure (FR-1.3, prd OQ-4)

Admin adds a member by creating the account directly (email + temporary password) and shares credentials out-of-band. Do not add SMTP, invitations, or token emails — explicitly out of scope for v1.

### Org isolation & authorization (AD-2)

- Member lists and all membership mutations are org-scoped. API cross-org → `404`; web UI cross-org → `403`.
- Admin-only endpoints must enforce the admin role server-side (the caller's `OrgMembership.role == "admin"` for the target org). UI hiding (AC #8) is UX, not security.

### Endpoints (solution-design.md §5.2 + spine)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/orgs/members/` | Yes | List org members |
| `POST` | `/api/v1/orgs/members/` | Yes | Create member account (admin only) |
| `DELETE` | `/api/v1/orgs/{org_id}/members/{user_id}/` | Yes | Remove member (admin only) |

(Create-org, transfer-admin, and leave-org endpoints are added at story level under `/api/v1/orgs/`, bound only by the `/api/v1/` prefix.)

### Testing standards

- Unit tests, Django test DB. The invariant tests are the highest-value cases — cover all three violation paths and assert the exact error string.
- Assert no email is sent on add-member (no mail backend calls).
- ≥90% coverage; mypy strict; structlog events bind `org_id`, `user_id`.

### Constraints / guardrails

- Depends on Stories 2.1 (models) and 2.2 (session auth / active org, admin identity). Uses the org-resolution helper from 2.2.
- AD-1: `users/` base layer, no feature-app imports.
- Reuse `create_org` — do not duplicate org+admin-membership creation logic.

### Project Structure Notes

- All under `backend/<project_slug>/users/`. Membership management UI page in `frontend/src/pages/`; API via `frontend/src/api/orgs.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3: Org Administration & Membership Management]
- [Source: solution-design.md#3.1 users/ — services/selectors]
- [Source: solution-design.md#5.2 Endpoint inventory]
- [Source: solution-design.md#10. Security Design — Org isolation]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: prd.md#FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.7]
- [Source: prd.md#Open Questions — OQ-4 invitation flow]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
