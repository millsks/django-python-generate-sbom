---
baseline_commit: aa61f9f
---

# Story 22.12: Close the Post-Refactor Suite Audit Findings

Status: review

> **Written after implementation** and backfilled on 2026-08-18; see the note in Story 22.5.

> **Added mid-epic**, answering the product owner's question — asked three times, which is why it became a
> story rather than a remark: *"are all of the unit and integration tests still valid? do any of them need
> to be purged or even rewired after the refactor of the application?"*

## Story

As a maintainer,
I want the things that merely *look* covered to be either real or gone,
so that a green suite means what it appears to mean.

**Context:** The audit of the suite after the Epic 21/22 refactor found three problems of the same kind —
something that presents as covered or enforced and is neither.

## Acceptance Criteria

1. **The fake security boundary is deleted.** `get_org_scoped_object_or_404` was documented as the
   org-isolation boundary and had **zero callers**; every real lookup went through `.for_org()`.
2. **The no-organizations state is covered on every surface.** Pages answer 200 with an explanation, the
   API answers its documented `{error, code}` envelope, and nothing 500s.
3. **The order-dependent test landmine is removed.** Test-only `_ScopedThing` made *any* `Org` delete fail
   with `no such table` once its module was collected.
4. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Delete `get_org_scoped_object_or_404` and rewrite the module docstring (AC: #1)**
  - [x] Name `.for_org()` as the real mechanism, so the next reader looks in the right place.
- [x] **Task 2 — Cover the no-organizations state (AC: #2)**
  - [x] Pages: `tests/unit/test_no_organizations_state.py`, including that seeding recovers the app.
  - [x] API: `tests/unit/test_users_api_error_envelopes.py`, one sweep across every refusal path.
- [x] **Task 3 — Create tables for models declared under `tests/` (AC: #3)**
- [x] **Task 4 — Gate (AC: #4)**

## Dev Notes

### The three findings, and why they are one finding

1. A function whose **name and docstring claim to be the security boundary** while enforcing nothing. Worse
   than no function, because it invites the next reader to trust it.
2. A state — no organization exists — that **every org-scoped surface depends on** and nothing tested.
   Because `get_admin_org` has been `get_request_org` since Story 21.24, this turned out to be the same
   condition behind nearly all of `users/views.py`'s uncovered lines: the `not_admin` 403s now fire when
   the database has **no org at all**, not because a caller lacks privilege.
3. A **pass/fail that depends on test collection order** — passing in isolation, failing in a full run.

### Traps

- **Coverage cannot see a dead module constant.** A module-level assignment always executes. This is why
  `users/views.py` read 100% while still defining `_NOT_GLOBAL_ADMIN` and `_INVALID_CREDENTIALS`, refusals
  the app cannot make (removed in Story 22.13).
- **The `_NOT_ADMIN` wording is stale and deliberately left alone.** Epics 17-18 restore a real admin
  decision at that seam and make it true again; a test pins the current text so changing it is deliberate.
- **Create tables only for models declared under `tests/`.** A blanket "create any missing table" would
  mask a genuinely missing migration for application code.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. **888 passed**, coverage **97.05%**.
- `common/access.py` **17/17 (100%)**; `users/views.py` **220/220 (100%)**, from 89% with 25 uncovered lines.
- The landmine was proven real: before the conftest fixture, **19 errors** in a full run
  (`no such table: inventory__scopedthing`) against 0 when the modules ran alone.

### Completion Notes List

**One scenario closed two findings.** Writing the no-organizations tests for the pages revealed that the
API's uncovered branches were the same condition, so the second module fell out of the first rather than
being a separate coverage exercise.

**The API module asserts a contract, not a percentage.** These endpoints are consumed by code: every
`@extend_schema` promises `{error, code}`, and a client branching on `code` breaks silently if a path
returns a bare DRF `{"detail": ...}`. It is asserted as one sweep across the surface for that reason.

**The landmine was fixed at the cause.** `_ScopedThing` registers in the `inventory` app registry for the
whole session with a cascading FK to `Org` — so the fix creates its table rather than teaching every
Org-deleting test to route around it.

### File List

**New (2)**
- `tests/unit/test_no_organizations_state.py` (10 tests)
- `tests/unit/test_users_api_error_envelopes.py` (27 tests)

**Modified (3)**
- `src/django_apps/inventory/common/access.py` — `get_org_scoped_object_or_404` deleted, docstring rewritten
- `tests/unit/conftest.py` — shared `no_organizations` fixture; session-scoped table creation for test models
- `sprint-status.yaml`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Closed three audit findings of one kind — things that look covered or enforced and are not. Deleted `get_org_scoped_object_or_404`, a zero-caller function documented as the org-isolation boundary. Covered the no-organizations state, which proved to be the same condition behind nearly all of `users/views.py`'s uncovered lines; both `access.py` and `views.py` reach 100%. Removed the collection-order landmine where a table-less test model made any `Org` delete fail (19 errors in a full run, 0 in isolation). 888 tests at 97.05%. |
