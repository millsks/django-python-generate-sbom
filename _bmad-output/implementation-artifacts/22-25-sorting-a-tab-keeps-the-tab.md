---
baseline_commit: 0fb92ff
---

# Story 22.25: Sorting a Results Tab Must Keep You on That Tab

Status: review

> **This is a bug fix, so the commit type is `fix:`** (global standards §5). Reported by the product owner:
> *"whenever I try to sort by a table header it doesn't actually sort. It just goes back to the Overview
> tab."*

## Story

As someone reading a report,
I want sorting a column to sort that column,
so that I am not thrown back to Overview and made to find my place again.

**Context:** django-tables2 builds each sort link by **preserving the current request's query string**. The
tab fragment is fetched at `/results/<id>/tab/<slug>`, which has no query string, so there was nothing to
preserve and the links came out as a bare `?sort=name`. Sorting is a full page navigation, so following one
landed on `/results/<id>?sort=name` — no `tab` — and the results view fell back to Overview. The sort was
applied; the reader just could not see it.

## Acceptance Criteria

1. **Sort links inside a tab fragment carry the tab.**
2. **Following one lands on the same tab**, sorted.
3. **The fix holds however the fragment is requested**, not only when htmx asks for it.
4. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Write the failing tests first, on the fragment (AC: #1, #2)**
- [x] **Task 2 — Declare the tab in the fragment request's GET (AC: #1, #3)**
- [x] **Task 3 — Verify against the running app, not only the test client (AC: #2)**
- [x] **Task 4 — Gate (AC: #4)**

## Dev Notes

### Why the view and not the template

The first fix appended `?tab={{ slug }}` to the `hx-get` URL in the tab strip. It worked for htmx and left
the view producing broken markup for any other caller — including the tests, which fetch the fragment
directly and were right to. A view that returns subtly wrong links when a parameter is omitted is a trap for
whoever adds the next caller, so the tab is declared in `request.GET` inside the view: correct however it is
reached, and no table has to know about it.

The `# type: ignore[assignment]` is django-stubs typing `request.GET` as immutable. Replacing it with a
mutable copy is the documented Django idiom.

### Traps

- **The full page gets this right on its own**, because there `request.GET` already contains `tab`. The bug
  existed only *after* a tab had been clicked, which is why a server-side check of the results page could
  never have found it — the first diagnostic run here did exactly that and came back clean.
- **The sort was working the whole time.** The complaint was "it doesn't actually sort", and the sort was
  applied — to a tab the reader was no longer looking at. Reproducing before believing the description
  mattered.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- Fragment links before: `?sort=-name`, `?sort=installed`. After: `?tab=versions&sort=-name`, etc.
- Following the first rendered link now lands on `active tab: ['versions']`; before, on Overview.
- 2 new tests in `tests/unit/test_results_page.py`, both red first for the right reason
  (`sort link drops the tab — ?sort=-name`).
- `pixi run ci` — **exit 0**, 1080 tests, 97.25%.

### Completion Notes List

**The first diagnostic exonerated the code, wrongly.** Fetching `/results/<id>?tab=versions&sort=installed`
renders the versions tab correctly, which made it look like there was nothing to fix. The difference is that
a person arrives at that tab through htmx, where the fragment — not the page — generates the links.
Reproducing the user's *path*, not just the user's *URL*, is what found it.

**A test fixture that skipped is a test that did not run.** The first version of these tests looked for sort
links, found none because the fixture job had no analysis report, and `pytest.skip`ped — passing green while
proving nothing. Replaced with a fixture that writes a real report to storage, so the tables actually render.

### File List

**Modified (2)**
- `src/django_apps/inventory/sbom/pages.py` — `JobTabPartialView` declares the tab in `request.GET`
- `tests/unit/test_results_page.py` — 2 tests and a report-bearing fixture

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Fixed sorting a results tab throwing the reader back to Overview. django-tables2 builds sort links by preserving the current query string, and the tab fragment is fetched at a URL that has none — so the links dropped `tab=` and a sort navigated to the results page with no tab selected. The sort had been applied all along, to a tab nobody was looking at. The tab is now declared in the fragment request's GET, so the links are right however the view is reached. |
