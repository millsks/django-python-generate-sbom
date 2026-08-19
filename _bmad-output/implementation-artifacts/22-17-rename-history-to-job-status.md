---
baseline_commit: ff3d251
---

# Story 22.17: Rename the History Page to Job Status

Status: review

> **Product-owner direction:** *"I would like to rename the history page to job status. let's do that for
> both the ui and for the api."*

> **A decision was taken back to the product owner first:** the API has no "history" naming to rename — the
> list is already `/api/v1/sbom/jobs/`, and `/api/v1/sbom/status/{task_id}/` owns "status" for a single job.
> **Answer: rename the documented name only; leave the paths.** The UI renames its paths in full.

## Story

As a user watching a job I just submitted,
I want the page to be called Job Status,
so that its name describes what it shows rather than only half of it.

**Context:** "History" was accurate when the page listed finished runs. Story 21.11 added live progress
polling, so it has shown *running* jobs ever since — someone watching a job they had just submitted was
looking at a page named for the past.

## Acceptance Criteria

1. **The UI renames its paths.** `/history` → `/job-status`, the three child routes with it, and
   `ui-history` → `ui-job-status`. No redirect and no alias: a rename that leaves the old URL working is
   two names, not one.
2. **The label, heading, nav entry and icon key follow**, and nothing still says History.
3. **The API paths do not move.** Story 21.24 AC #9 froze the `/api/v1/` contract, and a `/sbom/job-status/`
   list beside `/sbom/status/{task_id}/` would be worse than the inconsistency it fixed.
4. **The API's documented name does move** — OpenAPI summary and tag — so the reference and the UI agree.
5. **The docs follow**, including the user-guide page and the mkdocs nav.
6. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — URL paths, route name, view class, template file (AC: #1)**
- [x] **Task 2 — Nav label, icon key, page heading, the results page's back-link (AC: #2)**
- [x] **Task 3 — OpenAPI `summary` and `tags`, with the reason recorded in place (AC: #3, #4)**
- [x] **Task 4 — Docs: `job-history.md` → `job-status.md`, mkdocs nav, how-to, API reference (AC: #5)**
- [x] **Task 5 — Tests: rename the module, update paths, add the rename guard (AC: all)**
- [x] **Task 6 — Gate (AC: #6)**

## Dev Notes

### What must NOT be renamed

`HistoryPage.tsx` references are historical — they name the retired SPA file this page was converted from,
and rewriting them would make the comments wrong. `clock-history` is a Bootstrap icon name, not ours; the
registry **key** moved to `job-status` while the glyph stayed.

### Traps

- **`{% url 'ui-history' %}` fails at render time, not import time.** Only the page containing it breaks, so
  a missed one reaches a branch quietly. A test greps every template rather than visiting every page — two
  were missed on the first pass (`results.html`'s back-link and the filter "Clear" link) and this is what
  caught them.
- **`NAV_ITEMS` in `test_ui_shell.py` is a hand-kept list.** "History" moved to `REMOVED_ITEMS`, so having
  both names in the nav fails — the same drift, pointing the other way.
- **`test_landing_page.py` references `history.html` by filename** when checking that wide tables scroll.

### The stale doc this surfaced

`docs/user-guide/job-history.md` still said *"History is scoped to your active organization… check the
organization switcher in the top bar."* Story 22.16 removed the switcher and made the page cross-org, so
that guidance was already wrong. Rewritten rather than merely renamed, and the delete-all scope warning
added.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. **927 passed**, coverage **97.23%**.
- 14 new tests in `tests/unit/test_job_status_rename.py`; `test_history_page.py` renamed to
  `test_job_status_page.py`.

### Completion Notes List

**The two surfaces moved by different amounts, on purpose.** The UI renamed its paths because nothing
external depends on them. The API kept its paths because something might, and because the obvious target
name was already taken — `/api/v1/sbom/status/{task_id}/` means the status of one job, so a
`/sbom/job-status/` list beside it would read as the same thing at two paths. The reasoning is recorded in
the view, the schema and the API reference, since "why does the path say jobs when the UI says Job Status"
is exactly the question a reader will have.

**The rename guard asserts both halves**, including that no `/sbom/job-status/` path was added — the
tempting change is the one worth pinning against.

### File List

**New (1)**
- `tests/unit/test_job_status_rename.py` (14 tests)

**Renamed (3)**
- `templates/inventory/sbom/history.html` → `job_status.html`
- `docs/user-guide/job-history.md` → `job-status.md` (and rewritten)
- `tests/unit/test_history_page.py` → `test_job_status_page.py`

**Modified (14)**
- `urls_pages.py`, `sbom/{pages,views,tables,filters,selectors}.py`
- `django_service/{icons.py,views.py,context_processors.py}`, `templates/{_nav,_nav_item,shell_preview}.html`
- `templates/inventory/sbom/{results,_job_row,_job_progress}.html`
- `mkdocs.yml`, `docs/api/{jobs,index}.md`, `docs/user-guide/{index,generating-an-sbom}.md`,
  `docs/how-to/generate-sbom.md`
- `tests/unit/{test_ui_shell,test_landing_page,test_open_access,test_job_polling,test_spa_retirement,test_no_organizations_state,test_org_switcher_retirement}.py`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Renamed the History page to **Job Status**: it has shown running jobs since Story 21.11 added live polling, so the old name described half of what it does. The UI moved its paths (`/history` → `/job-status`, child routes and route name included, with no alias left behind); the API kept its paths, because the `/api/v1/` contract is frozen and `/sbom/status/{task_id}/` already owns "status" for a single job — only the OpenAPI summary and tag moved. Also rewrote the user-guide page, which still told readers to use the org switcher Story 22.16 deleted. |
