---
baseline_commit: fe655ae
---

# Story 22.8: Make the Admin Surfaces Work for an Anonymous Caller

Status: review

> **Written after implementation** and backfilled on 2026-08-18; see the note in Story 22.5.

> **Added mid-epic**, found by auditing whether the test suite was still valid after the Epic 21 refactor.

## Story

As an operator of an app with no authentication,
I want the surfaces Story 21.24 declared open to actually work when nobody is signed in,
so that the ordinary caller is not the one path nothing was tested against.

**Context:** Story 21.24 removed the app's authentication and stated (AC #5) that member management, org
creation, API-key create/revoke, bulk artifact deletion, and the global-admins page all remain reachable
and succeed. Two defects slipped through, and **the suite could not see either, because every page and API
test logs in first** — so nothing exercised the anonymous path that is now the ordinary one.

## Acceptance Criteria

1. **Org creation succeeds without a user.** `create_org` assigned `admin_user` to `OrgMembership.user`,
   and an `AnonymousUser` raises `ValueError: Cannot assign ...`. An anonymous request must create the org
   with **no** membership rather than a synthetic user.
2. **Signing in never removes capability.** Four DRF views kept in-body `is_global_admin()` checks;
   `is_global_admin` returns `True` for anonymous but does the real membership query for a real user — so
   signing in *lost* you access. Asserted as a **relationship**, not as two absolutes.
3. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Make `create_org`'s `admin_user` optional (AC: #1)**
  - [x] No synthetic user: `ManifestUpload.user` and `SBOMJob.user` are already nullable so userless work
        can be recorded, and an org with no memberships is the equivalent coherent state.
- [x] **Task 2 — Remove the four surviving in-body gates (AC: #2)**
- [x] **Task 3 — Write parity tests (AC: #2)**
- [x] **Task 4 — Gate (AC: #3)**

## Dev Notes

### Why the suite could not see this

Every page and API test calls `client.login(...)` first — 161 of 851 tests depended on it purely for tenant
selection. That was verified empirically by defeating `client.login` and counting the failures, rather than
assumed. The anonymous path, which is now the **ordinary** one, was untested end to end.

### Traps

- **Assert the relationship, not the absolutes.** What inverted was "anonymous can do more than signed-in".
  Two separate assertions (anonymous gets 200; signed-in gets 200) would both have been written to match
  whatever the code did. The parity test states: the anonymous caller must never succeed where a signed-in
  one is forbidden.
- **`is_global_admin` still reports truthfully; it no longer gates.** Do not delete it.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**.
- 134 lines of new tests in `tests/unit/test_anonymous_admin_surface.py`.

### Completion Notes List

**Two real defects, both invisible to a green suite.** Org creation returned **500** for an anonymous
caller on both the API and the page. And a logged-in ordinary user was **more restricted** than an
anonymous one on four endpoints — Story 21.24 removed the permission class and the page mixins but missed
the copies inside view bodies.

**No synthetic user was invented.** Story 21.24's notes rule that out explicitly, and `seed_orgs`
(Story 22.10) creates orgs with no user at all through the same path.

### File List

**New (1)**
- `tests/unit/test_anonymous_admin_surface.py`

**Modified (6)**
- `src/django_apps/inventory/users/services.py` — `create_org(name, admin_user=None)`
- `src/django_apps/inventory/users/views.py` — four in-body gates removed
- `src/django_apps/inventory/users/pages.py`
- `tests/unit/test_global_admin.py`, `tests/unit/test_membership.py`, `sprint-status.yaml`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Fixed two defects Story 21.24 left behind and no test could see, because every page and API test logs in first: anonymous org creation 500'd on `AnonymousUser`, and four DRF views kept in-body `is_global_admin()` checks that made **signing in more restrictive than staying anonymous**. Guarded by parity tests that assert the relationship rather than two absolutes — the relationship is what inverted. |
