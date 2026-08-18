---
baseline_commit: 7d3e64b
---

# Story 22.13: Reconcile the API Reference With the Removed Authorization

Status: review

> **Written after implementation** and backfilled on 2026-08-18; see the note in Story 22.5.

> **Added at the end of Epic 22**, surfaced by an `mkdocs build` INFO line about a broken anchor
> (`authentication.md#post-apiv1authregister`) — a link to an endpoint Story 21.24 deleted. Pulling that
> thread found the API reference still describing an authorization model the app no longer has.

## Story

As a reader of the API reference,
I want the documented gates to match what the app enforces,
so that I do not conclude an endpoint is protected when it is open.

**Context:** `docs/api/authentication.md` was updated by Story 21.24 and is accurate.
`docs/api/organizations.md`, `docs/api/api-keys.md`, and `docs/api/index.md` were missed. They still said
"Admin only", "Global admin only", and listed `403 not_global_admin` as a returned error on endpoints that
**cannot return it** — Story 22.8 removed the last in-body copy of that check.

**Documenting protection the app does not have is worse than documenting none**, because a reader stops
looking.

## Acceptance Criteria

1. **Every API page that describes endpoints states the true posture up front.**
2. **No page lists an error code the app cannot return.** `not_global_admin` and `invalid_credentials` are
   gone from the code and from the reference.
3. **The stale `403 not_admin` listings are explained rather than deleted** — the code *is* still returned,
   but only when the deployment has no organization at all.
4. **A test ties the docs to the code**, so this cannot rot again.
5. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Add the posture notice to `organizations.md` and `api-keys.md` (AC: #1)**
- [x] **Task 2 — Delete the dead constants `_NOT_GLOBAL_ADMIN` and `_INVALID_CREDENTIALS` (AC: #2)**
- [x] **Task 3 — Correct the error listings and the `index.md` code list (AC: #2, #3)**
- [x] **Task 4 — Fix the broken anchor to the deleted registration endpoint (AC: #1)**
- [x] **Task 5 — Add the retired-code tests (AC: #4)**
- [x] **Task 6 — Gate (AC: #5)**

## Dev Notes

### Why the admin markers were kept

They record the authorization each endpoint is *meant* to carry, and Epics 17-18 restore that decision from
host-supplied OIDC group claims at the same seam. Deleting them would lose the intent; leaving them
unqualified would claim protection. So each page carries one prominent, accurate notice, and the markers
point at it.

### Traps

- **`403 not_admin` is not dead** — unlike `not_global_admin`. It fires when `get_admin_org` returns `None`,
  which since Story 21.24 means *no organization exists*, not *insufficient privilege*. Deleting it from the
  docs would have been as wrong as leaving it unexplained.
- **Coverage cannot catch a dead constant.** Both removed constants sat in a module that read 100%.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. **898 passed**, coverage **97.05%**.
- 4 new tests in `tests/unit/test_users_api_error_envelopes.py`.
- **Both new tests failed red on their first run** and caught real leftovers — including
  `not_global_admin` in the very code comment written to explain its removal, and in the posture notice
  drafted moments earlier.

### Completion Notes List

**The test that catches this is mechanical, not stylistic.** It asserts the retired codes appear nowhere in
`src/`, and that no API page mentions them without saying they are retired. That second form allows the two
sentences that *document* the removal while banning a fresh claim.

**Found by an INFO line, not a failure.** `mkdocs build --strict` reports a broken anchor as INFO, so the
gate was green while the reference pointed at a deleted endpoint. Worth knowing: strict mode does not make
intra-page anchors fatal.

### File List

**Modified (5)**
- `docs/api/organizations.md`, `docs/api/api-keys.md`, `docs/api/index.md`
- `src/django_apps/inventory/users/views.py` — two dead constants removed
- `tests/unit/test_users_api_error_envelopes.py` — 4 tests

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Reconciled the API reference with the authorization Story 21.24 removed: pages claimed "Admin only" gates and listed `403 not_global_admin` on endpoints that cannot return it. Each page now states the true posture up front and keeps the admin markers as recorded intent for Epics 17-18. Removed the dead `_NOT_GLOBAL_ADMIN` and `_INVALID_CREDENTIALS` constants, which coverage could not see. Two new tests pin that neither code appears in `src/` nor is promised by a doc page — both caught real leftovers on their first run. |
