---
baseline_commit: b36330b
---

# Story 22.11: Remove the Organization UI

Status: review

> **Written after implementation** and backfilled on 2026-08-18; see the note in Story 22.5.

> **Added mid-epic by product-owner direction:** *"let's remove the rest of the organization code. there is
> no need for it is there? you can then remove it from the nav table?"*

## Story

As a user,
I want the navigation to reflect that orgs are seeded, not created,
so that the app does not offer a form that duplicates a committed file.

**Context:** With Story 22.10 seeding orgs from `orgs.yml`, the creation form is redundant, and the
organization hub only linked to surfaces the nav already offers. This completes what Story 22.9 started.

## Acceptance Criteria

1. The Organization pages, routes, templates, and nav entry are removed; the nav is
   **Home / Upload / History / API Keys**.
2. **Orgs remain first-class data.** The header switcher selects one and the upload form files a job
   against one; only the management UI goes.
3. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Remove the hub and create pages, routes, templates, and the form (AC: #1)**
- [x] **Task 2 — Nav down to four items (AC: #1)**
- [x] **Task 3 — Repoint `_no_orgs.html` at the remedy that now exists (AC: #2)**
  - [x] The page previously implied you could create one from the UI; it now names `pixi run seed-orgs`.
- [x] **Task 4 — Update the tests that referenced the removed pages**
- [x] **Task 5 — Gate (AC: #3)**

## Dev Notes

### Traps

- **The `_no_orgs.html` template had to change with this story**, not after it. With the creation form
  gone, a page telling the visitor to create an organization pointed at nothing.
- **Same `pages.py` helper trap as Story 22.9** — the module-level constants live between the classes.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Net **-233 lines**.

### Completion Notes List

**Orgs did not stop mattering; only their management UI went.** The switcher, the upload form's org
binding, and every `.for_org()` scope are untouched. This is the same line Story 22.9 drew.

**Open item for the product owner:** with the creation UI gone there is no in-app escape hatch for adding
an org, so registering `Org` in the Django admin may be worth doing. Not done here — it is a separate
decision about what `/admin/` exposes.

### File List

**Deleted (2)**
- `templates/inventory/orgs/{hub,create}.html`

**Modified (11)**
- `users/pages.py`, `users/forms.py`, `urls_pages.py`, `_nav.html`, `_no_orgs.html`,
  `tests/unit/test_org_pages.py`, `test_ui_shell.py`, `test_spa_retirement.py`,
  `test_anonymous_admin_surface.py`, `test_open_access.py`, `sprint-status.yaml`

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Removed the Organization hub and creation form, which Story 22.10 made redundant, and cut the nav to Home / Upload / History / API Keys. `_no_orgs.html` was repointed at `pixi run seed-orgs` in the same change, since the page it used to send people to no longer exists. Orgs remain first-class data — the switcher and the upload form still bind to one. |
