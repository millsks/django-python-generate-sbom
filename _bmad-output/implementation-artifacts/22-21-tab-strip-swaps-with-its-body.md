---
baseline_commit: 705045a
---

# Story 22.21: Swap the Tab Strip With the Tab It Shows

Status: review

> **This is a bug fix, so the commit type is `fix:`** (global standards §5). Reported by the product owner:
> *"I click on one of the tabs and it stays on Overview, but I see a faint outline of the tab that I clicked
> on."*

## Story

As someone reading a job's results,
I want the highlighted tab to be the tab I am looking at,
so that the page does not appear stuck on a tab it is no longer showing.

**Context:** The tab bodies were loading correctly the whole time — the screenshot showed the Version
Currency table rendered under a highlighted **Overview**. htmx targeted `#tab-content` alone, so the tab
strip stayed exactly as the server first rendered it and the `active` class never moved. The clicked tab
showed only the browser's focus outline, which is what made it look like nothing had happened.

## Acceptance Criteria

1. **The strip and the body are swapped together**, so they cannot disagree about which tab is showing.
2. **The strip is defined once** and included by both the full page and the htmx fragment.
3. **The fragment carries every tab**, not just the active one — otherwise a click would strand the reader.
4. **The URL still tracks the tab** (`hx-push-url`), and a bookmarked `?tab=` still renders server-side.
5. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Extract `_result_tabs.html` (AC: #2)**
- [x] **Task 2 — Wrap strip + body in `_tab_panel.html` under `#tab-panel` (AC: #1)**
- [x] **Task 3 — Retarget the anchors to `#tab-panel` with `outerHTML` (AC: #1)**
- [x] **Task 4 — `JobTabPartialView` renders the panel and supplies what the strip needs (AC: #3)**
- [x] **Task 5 — Gate (AC: #5)**

## Dev Notes

### Why the whole panel rather than an out-of-band update

`hx-swap-oob` would have worked and needs the nav markup in two places, or a second render of it. Swapping
one wrapper keeps the `active` computation in a single template, which is the property that stops this
recurring: two copies of "which tab is active" drift, and the drift is invisible until someone clicks.

### Traps

- **The tab fragment now needs the strip's context** — `tabs`, `artifact_tabs`, `active_tab_template`. It
  previously rendered only a body and needed none of them.
- **The bug is invisible on first load.** Server-side rendering gets the active class right every time; only
  a *click* exposes it. A test that checks the full page passes regardless — the assertions here read the
  fragment htmx actually receives, per tab.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- 6 new/updated assertions in `tests/unit/test_results_page.py`.
- **Ablation:** restoring the body-only render fails 6 tests (one per tab, plus the whole-strip check);
  restoring the panel render passes all 31.
- `pixi run ci` — **exit 0**, 960 tests, 97.24%.
- Confirmed working by the product owner.

### Completion Notes List

**The content was never broken.** Reading the screenshot rather than the description was what located this:
the Version Currency table was on screen under a highlighted Overview, so the swap was working and only the
strip was stale. A page that renders the right thing under the wrong label is a harder bug to describe than
one that renders nothing.

**The existing test asserted the mechanism, not the outcome.** `test_tabs_load_their_content_over_htmx`
checked for `hx-target="#tab-content"` — it would have kept passing forever while the bug persisted, because
it pinned the very thing that was wrong. It now asserts the target *and* which tab comes back active.

### File List

**New (2)**
- `templates/inventory/sbom/_result_tabs.html`, `_tab_panel.html`

**Modified (3)**
- `templates/inventory/sbom/results.html` — includes the panel
- `src/django_apps/inventory/sbom/pages.py` — `JobTabPartialView` renders the panel
- `tests/unit/test_results_page.py`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Fixed the results tabs appearing not to switch. htmx targeted `#tab-content` alone, so the tab strip kept the `active` class the server first rendered — the clicked tab's content loaded under a highlighted "Overview". The strip and body are now one swap target rendered from one template, so they cannot disagree. The old test asserted the broken target itself and would have passed indefinitely. |
