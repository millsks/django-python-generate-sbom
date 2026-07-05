# Story 2.8: Global Admin Org & Cross-Org Provisioning

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the platform owner,
I want a global-admin tier that oversees every organization,
so that platform admins can manage all orgs.

## Acceptance Criteria

1. **System ADMIN org.** A system **ADMIN** org exists (a distinguished `Org`, via a flag/slug); its members are **global admins**; the initial/superuser is seeded into it.
2. **Cross-org provisioning.** Every global admin is a **full admin of ALL orgs, existing and future**: (a) creating any org auto-adds all global admins as admins; (b) granting global-admin (adding a user to the ADMIN org) **back-fills** that user as an admin into **all existing orgs**.
3. **Managing the ADMIN org.** **Existing global admins can add other users to the ADMIN org** (growing the set), starting from the seeded superuser.
4. **Deliberate, documented superuser tier.** This is a cross-org superuser tier that bypasses normal org isolation. The elevated access is deliberate and documented; permission checks treat global admins as org admins everywhere; tests cover seeding, auto-add on org create, back-fill on grant, and global-admin-only management of the ADMIN org.

## Tasks / Subtasks

- [ ] **Task 1 — Model + migration (AC: #1)**
  - [ ] Add `is_admin_org = models.BooleanField(default=False)` to `Org` (`backend/generate_sbom/users/models.py:58`). Document in the docstring that exactly one org is the ADMIN org and its members are global admins (a deliberate cross-org superuser tier).
  - [ ] `makemigrations users` → schema migration (`0003_org_is_admin_org`).
- [ ] **Task 2 — Seed the ADMIN org + superuser (AC: #1)**
  - [ ] **Data migration** (`0004_seed_admin_org`): create the ADMIN org row (`name="Admin"`, `slug="admin"`, `is_admin_org=True`) if absent (idempotent, `get_or_create`).
  - [ ] Hook superuser creation: override `UserManager.create_superuser` (`models.py:33-39`) to call `services.grant_global_admin(user)` after creation so any new superuser becomes a global admin. Guard for the ADMIN org not existing yet (migrations may not have run) — `grant_global_admin` already returns early when `get_the_admin_org()` is `None`.
  - [ ] Provide an idempotent management command (e.g. `bootstrap_admin_org`) that ensures the ADMIN org exists and back-fills all existing `is_superuser` users as global admins — so already-created superusers are covered.
- [ ] **Task 3 — Provisioning services (AC: #2, #3)**
  - [ ] In `backend/generate_sbom/users/services.py`, add: `get_the_admin_org() -> Org | None` (first `is_admin_org=True` org); `is_global_admin(user) -> bool` (membership in the ADMIN org); `_global_admins() -> list[User]`; `_provision_global_admins(org)` (make every global admin an ADMIN of `org`, idempotent via `update_or_create`); `grant_global_admin(user)` (add to ADMIN org + back-fill as admin into every non-admin org).
  - [ ] Call `_provision_global_admins(org)` at the end of `create_org()` so new orgs auto-add global admins (AC #2a). Do **not** provision inside `register_user` — Story 2.6 made registration create no org.
- [ ] **Task 4 — Permission integration (AC: #4)**
  - [ ] Because global admins get **real ADMIN memberships** in every org, `get_admin_org`/`get_request_org` (`auth.py`) already treat them as admins — verify this holds and add a test rather than special-casing. If any authorization path checks memberships in a way that would miss a global admin, reconcile it here.
  - [ ] Add an endpoint/service for AC #3: a global-admin-only action to add another user to the ADMIN org (i.e. `grant_global_admin`), gated so **only existing global admins** can call it.
- [ ] **Task 5 — Docs (AC: #4)**
  - [ ] Document the global-admin tier (what it is, that global admins appear in every org's roster and bypass isolation deliberately) in the developer docs / architecture notes.
- [ ] **Task 6 — Tests (AC: #4)**
  - [ ] Seeding (ADMIN org exists after migrate; superuser is a global admin via the hook/command); auto-add on `create_org` (new org contains all global admins as admins); back-fill on `grant_global_admin` (existing orgs gain the new global admin as admin); global-admin-only management of the ADMIN org (non-global-admin is rejected); a global admin is treated as admin on an org they never explicitly joined.

## Dev Notes

### Reference design (from the prior, discarded attempt)

An earlier attempt implemented the service layer roughly as below (it was discarded because it lacked the migration, seeding, permission tests, and broke registration callers). Reuse this shape:

```python
ADMIN_ORG_NAME = "Admin"
ADMIN_ORG_SLUG = "admin"

def get_the_admin_org() -> Org | None:
    return Org.objects.filter(is_admin_org=True).first()

def is_global_admin(user: User) -> bool:
    admin_org = get_the_admin_org()
    return admin_org is not None and OrgMembership.objects.filter(org=admin_org, user=user).exists()

def _global_admins() -> list[User]:
    admin_org = get_the_admin_org()
    return [] if admin_org is None else list(User.objects.filter(org_memberships__org=admin_org))

def _provision_global_admins(org: Org) -> None:
    for user in _global_admins():
        OrgMembership.objects.update_or_create(org=org, user=user, defaults={"role": OrgMembership.Role.ADMIN})

def grant_global_admin(user: User) -> None:
    admin_org = get_the_admin_org()
    if admin_org is None:
        return
    OrgMembership.objects.get_or_create(org=admin_org, user=user, defaults={"role": OrgMembership.Role.ADMIN})
    for org in Org.objects.filter(is_admin_org=False):
        OrgMembership.objects.update_or_create(org=org, user=user, defaults={"role": OrgMembership.Role.ADMIN})
```

### Key design decisions the prior attempt missed

- **Seeding mechanism.** Prefer a **data migration** for the ADMIN org row (deterministic across environments) plus a `create_superuser` override calling `grant_global_admin`, backed by an idempotent `bootstrap_admin_org` management command for already-existing superusers. Do not rely on a nonexistent "superuser hook" — build one of these.
- **Migration required.** The prior attempt added `is_admin_org` with no migration — the app would fail `makemigrations --check` and DB writes would error. Ship both the schema and data migrations.
- **Global admins are real memberships.** Because provisioning writes actual `OrgMembership(role=ADMIN)` rows, existing permission checks (`get_admin_org`, `get_request_org` in `auth.py`) work unchanged — no bespoke "is this a global admin?" branch in every view. This is the simplest correct integration; verify with tests instead of adding special cases.
- **Consequence to document:** global admins show up in every org's member roster and count as admins there. That is intended (AC #4) but must be called out for Story 2.9's edge rules (a global admin must not be strandable / must not be the blocker for "last admin").

### Current state of touched files

- `Org` model — `models.py:58-67` (no `is_admin_org` today). `UserManager.create_superuser` — `models.py:33-39`. `create_org` — `services.py:30-37` (creator-as-admin only). `OrgMembership` (unique `(org, user)`) — `models.py:70-87`. `get_admin_org`/`get_request_org` — `auth.py`. Users migrations today: `0001_initial`, `0002_orgapikey`.

### Cross-story dependencies

- **Story 2.6** must land first (registration creates zero orgs; the superuser has no personal org and is seeded here into the ADMIN org). 2.6 + 2.8 together are the membership-model foundation.
- **Story 2.5** AC #2 (auto-add global admins on org create) is satisfied by Task 3 here.
- **Story 2.7** AC #1 ("non-global-admins") and **Story 2.9** (edge cases) both depend on this story's global-admin model. Recommended order: 2.6 → 2.8 → 2.5/2.7 → 2.9.

### Testing standards

- Backend: pytest `@pytest.mark.django_db`, DRF `APIClient`, `backend/tests/unit/`. Coverage gate ≥90% via `pixi run cov`. Test the management command with `call_command`.

### Project Structure Notes

- Backend `backend/generate_sbom/users/{models,services,auth}.py`, new migration(s) in `backend/generate_sbom/users/migrations/`, new management command under `backend/generate_sbom/users/management/commands/`. Docs under `docs/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.8: Global Admin Org & Cross-Org Provisioning] (lines 614-643)
- [Source: _bmad-output/planning-artifacts/epics.md — Epic 2 reopened decisions] (lines 528-531)
- Backend: `backend/generate_sbom/users/models.py:33`, `models.py:58`, `services.py:30`, `auth.py:58`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
