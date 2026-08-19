---
baseline_commit: a29636d
---

# Story 22.9: Remove the Inert Membership and Global-Admin UI

Status: review

> **Written after implementation** and backfilled on 2026-08-18; see the note in Story 22.5.

> **Added mid-epic by product-owner direction:** *"do we need the members, api keys, organizations, and
> global admins tabs on the left any longer? … if that functionality is no longer needed i would rather get
> rid of it."*

## Story

As a user,
I want the navigation to offer only what still does something,
so that a screen does not imply an access-control decision the app no longer makes.

**Context:** Members, Global Admins, and the leave-org action all edited records that gate nothing without
identity — and all three were **broken for the anonymous caller** that is now the ordinary one:
`/organization/leave` raised `TypeError` on `AnonymousUser`. Hiding them was considered and rejected in
favour of removal, on the product owner's instruction.

## Acceptance Criteria

1. The pages, routes, templates, nav entries, and forms for Members, Global Admins, and leave-org are removed.
2. **The org and membership model, the services, and the `/api/v1/` endpoints are retained.** The model is
   the seam OIDC group claims re-attach to (Epics 17-18), and Story 21.24 AC #9 froze the API surface.
3. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Remove the page views, routes, templates, and forms (AC: #1)**
- [x] **Task 2 — Update the nav (AC: #1)**
- [x] **Task 3 — Confirm the model, services, and API are untouched (AC: #2)**
- [x] **Task 4 — Purge the tests that covered the removed surfaces**, and update the ones that merely
      referenced them
- [x] **Task 5 — Gate (AC: #3)**

## Dev Notes

### Traps

- **`pages.py` holds module-level helpers between the view classes** (`KEYS_TEMPLATE`, `_keys_context`,
  `KEY_NOT_FOUND`). A script that deletes "from `class X`" to "the next `class`" swallows them. This bit
  twice during implementation; both times the helpers were restored from git.
- **Deleting a page's tests is not the same as deleting its coverage.** Several tests in
  `test_org_pages.py` and `test_ui_shell.py` asserted on nav contents in passing and needed updating, not
  removing.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Net **-1,097 lines**.

### Completion Notes List

**Removal rather than hiding, on explicit instruction.** A hidden page is still reachable by URL and still
implies a decision the app does not make.

**The API and model stayed.** This is the line the story is drawn along: the *UI* for an authorization
model the app no longer enforces is misleading; the *model* is the seam that authorization comes back
through in Epics 17-18.

### File List

**Deleted (5)**
- `templates/inventory/orgs/{members,member_created}.html`, `templates/inventory/platform/global_admins.html`,
  `tests/unit/test_global_admin_pages.py`, and the leave-org route/view

**Modified (10)**
- `users/pages.py` (-277), `users/forms.py` (-49), `urls_pages.py`, `_nav.html`,
  `tests/unit/test_org_pages.py`, `test_ui_shell.py`, `test_spa_retirement.py`, `test_landing_page.py`,
  `test_open_access.py`, `sprint-status.yaml`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Removed the Members, Global Admins, and leave-org surfaces — all edited records that gate nothing without identity, and all three were broken for the anonymous caller (`/organization/leave` raised `TypeError`). The org/membership model, services, and `/api/v1/` endpoints are retained: the model is the seam OIDC group claims re-attach to. Net -1,097 lines. |
