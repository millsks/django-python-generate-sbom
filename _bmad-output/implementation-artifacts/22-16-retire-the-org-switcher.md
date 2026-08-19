---
baseline_commit: 316bb7f
---

# Story 22.16: Retire the Org Switcher; the Organization Is Provenance

Status: review

> **Added by product-owner direction:** *"we no longer need the org switcher. the orgs are selected in the
> upload form and should be added to the sbom with the other metadata."* Story 22.14 delivered the SBOM
> half; this is the UI half.

> **Two decisions were taken to the product owner before any code was written**, because both materially
> changed the work: what the pages scope to once the switcher is gone (**answer: the organization becomes
> metadata; History lists every org with a column and a filter**), and how the org appears in the document
> (**answer: each format's own supplier field**).

## Story

As a user,
I want the organization to be a property of a job rather than a mode the whole UI sits in,
so that I choose it once, at submission, and can still see everything afterwards.

**Context:** The switcher put the entire UI into a mode. Since Story 21.24 removed authentication it also
accepted **any** non-ADMIN org from **anyone** — so the mode it selected was never a permission, just a
filter wearing a permission's clothes, two clicks from the page you were reading.

## Acceptance Criteria

1. **The switcher is gone** — template, view, route, and its context-processor entry.
2. **History spans every organization**, with an Organization column and an org filter beside Status and
   Format.
3. **The rows open.** Results, tabs, progress polling, the raw SBOM view, and the Excel exports all serve
   any org's job; an unknown id still 404s.
4. **The API keeps its org scoping.** An API key pins one tenant (AD-8), so `get_jobs` stays scoped while
   the pages move to `get_all_jobs`.
5. **"Delete all artifacts" does not silently widen.** It acts on what the table is showing, and the
   confirmation says which.
6. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Split the selectors (AC: #3, #4)** — add `get_all_jobs` / `get_any_job`, keep `get_jobs` /
      `get_job` for the API, extract the shared filter helper so "In Progress" has one definition
- [x] **Task 2 — Point the pages at the cross-org selectors (AC: #3)**
- [x] **Task 3 — Organization column and filter (AC: #2)**
- [x] **Task 4 — Delete the switcher (AC: #1)**
- [x] **Task 5 — Contain the delete-all blast radius (AC: #5)**
- [x] **Task 6 — Invert the tests that asserted the old rule, rather than deleting them (AC: #3)**
- [x] **Task 7 — Gate (AC: #6)**

## Dev Notes

### The delete-all hazard, which was not in the request

Making History cross-org silently turned **"delete every artifact in my org"** into **"delete every artifact
in the deployment"** — same button, same confirmation still naming a single organization, vastly larger
blast radius. Four failing tests surfaced it.

It now re-applies the History filters from the submitted form, so it deletes exactly what was on screen, and
the confirmation is built server-side (the template cannot resolve an org id to a name, and a confirmation
that misdescribes what it is about to delete is worse than none). Filtered to one org, it stays there;
unfiltered, it says `EVERY job in EVERY organization`.

### AD-2 is narrowed, not abandoned

Org isolation now binds the **API**, where an API key genuinely pins a tenant. It no longer binds the pages.
This is not a reduction in real isolation: since Story 21.24 anyone could switch to any non-ADMIN org, so
"another org's job" was always reachable. The switcher made that a detour; this makes it honest. **This
should be recorded as an AD-2 amendment** — flagged for the architecture reconciliation.

### Traps

- **`django_service/views.py` keeps `LANDING_FEATURES` / `LANDING_STEPS` between the classes.** Cutting
  "from `class OrgSwitchView`" to "the next `class`" eats them — the same trap Stories 22.9 and 22.11
  documented, walked into anyway and caught by mypy.
- **Deleting `_org_switcher.html` without removing its `{% include %}` 500s every page.** A test asserts no
  template still references it.
- **Twelve tests asserted the old scoping.** They were *inverted*, not deleted: the property changed, and a
  test that used to assert a 404 and now asserts a 200 is the clearest record of that.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- Removing the switcher failed **28 tests**; every one was an intended consequence.
- `tests/unit/test_org_switcher.py` (14 tests) deleted, replaced by `test_org_switcher_retirement.py` (11).
- `pixi run ci` — **exit 0**, 913 tests.

### Completion Notes List

**The four tests that mattered were the destructive ones.** Three inverted-scoping failures were expected;
the two delete tests exposed a hazard nobody asked about. That is the argument for running the suite before
believing a UI change is finished.

**Inverted, not deleted.** Twelve tests asserted org isolation on the pages. Deleting them would have left
no record that the rule changed; each now states the new rule and why, including
`test_another_orgs_job_is_reachable_but_an_unknown_id_is_not`, which used to assert the opposite.

**One test module replaced another.** The switcher's 14 tests — CSRF, `next` handling, refusing the ADMIN
org — had no subject left. The retirement module pins the deletion and the three surfaces that replaced it.

### File List

**New (1)**
- `tests/unit/test_org_switcher_retirement.py` (11 tests)

**Deleted (2)**
- `src/django_service/templates/_org_switcher.html`, `tests/unit/test_org_switcher.py`

**Modified (12)**
- `src/django_apps/inventory/sbom/{selectors,pages,tables,filters}.py`
- `src/django_service/{views,context_processors}.py`, `src/config/urls.py`
- `src/django_service/templates/base.html`, `templates/inventory/sbom/history.html`
- `tests/unit/{test_open_access,test_history_page,test_results_page,test_job_polling,test_sbom_tab,test_excel_export,test_versions_tab,test_licenses_tab,test_vulnerabilities_tab}.py`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Removed the header org switcher. The organization is chosen on the upload form, shown as a History column with its own filter, and written into the SBOM as its supplier (Story 22.14) — provenance rather than a mode. Pages went cross-org via new `get_all_jobs`/`get_any_job`; the API kept `get_jobs`/`get_job`, because an API key really does pin a tenant. Caught and contained a hazard the change introduced: "delete all artifacts" would have widened from one org to the whole deployment, and now follows the on-screen filter with a confirmation that names its own scope. Twelve tests were inverted rather than deleted. |
