---
baseline_commit: a2c627e
---

# Story 22.27: Stop Tests Pinning Configuration, and Fix a Windows-Only Path Comparison

Status: review

> **Raised by the product owner:** *"fix the failing tests"* — after renaming the product to **PyFABRIC** in
> commit `a2c627e`. The rename was fine; the tests were wrong.

## Story

As someone renaming the product,
I want the suite to keep passing,
so that changing a configured value is a configuration change and not a test-editing exercise.

**Context:** Story 21.3 made the product name a single definition in settings precisely so it could be
changed in one place. Story 22.23's tests then **pinned the literal value** in five places, which undid
that: the next rename failed the suite. Separately, `test_documentation_accuracy.py` compared
`str(path.relative_to(DOCS))` against `mkdocs.yml`, which renders backslashes on Windows — so every page
looked unlisted and the whole Windows job failed.

## Acceptance Criteria

1. **No test pins the product name's value.** They assert properties, read from settings.
2. **The docs nav check is separator-independent.**
3. **The same path mistake cannot recur**, anywhere in the suite.
4. **The landing page's tests describe what it does now**, after the product owner removed the heading's
   line break in `a2c627e`.
5. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Derive the name from `settings` in all five tests (AC: #1)**
- [x] **Task 2 — `as_posix()` in the nav check (AC: #2)**
- [x] **Task 3 — Guard the pattern across `tests/`, and convert the five other instances (AC: #3)**
- [x] **Task 4 — Retire the heading-split test and its now-orphaned helper (AC: #4)**
- [x] **Task 5 — Gate (AC: #5)**

## Dev Notes

### The rule the tests broke

A test that hardcodes a configured value converts every configuration change into a test failure. Worse, it
does so **silently at authoring time** — the test passes when written, and only the next person to exercise
the configuration discovers the cost. Properties survive: *the brand shows the short form and not the long
one*, *the acronym has no dots*, *the product name differs from the distribution name*.

### What `a2c627e` also changed

The same commit replaced the landing heading's `{% for line in product_name_lines %}` loop with plain
`{{ product_name }}`, removing the break after the ampersand that had been requested one story earlier. It
is left removed — that is the product owner's file — and the consequences are tidied rather than reverted:
the template comment describing a break that no longer happens is corrected, and `_heading_lines` is deleted
because nothing called it any more. **Flagged for the product owner** in case it was collateral.

### Traps

- **A guard that matches its own source.** The new check greps `tests/` for the pattern, and both its
  docstring and its own regex literal contained it. The regex is built from two pieces and the docstring
  reworded — a self-matching guard is worse than none, because the fix is to weaken it.
- **Only comparisons matter, not messages.** Backslashes in a failure string are cosmetic. The five other
  instances found were all message-building, and were converted anyway: one rule is easier to hold than a
  rule with an exemption, and `as_posix()` is never worse.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- Local failures before: 5 (`PyFABRIC` vs the pinned `FABRIC`, and the pinned full name).
- Windows CI failure: `these pages are not reachable from the nav: ['api\\analysis.md', …]` — all 36 pages.
- The new guard found **five further instances** of the same path pattern on its first run.
- `pixi run ci` — **exit 0**, 1093 tests, 97.26%.

### Completion Notes List

**Both defects were mine, and both were in tests rather than the product.** The suite was asserting things
nobody had agreed to: that the product is called FABRIC, and that a rendered path uses the author's
separator. Neither is a property of the application.

**The Windows failure is the more instructive one.** It passed on macOS, passed on Linux, and failed the one
platform this epic exists to protect — the same shape as Stories 22.7, 22.15 and 22.18. A guard that bans the
pattern across the whole suite is worth more than the one-line fix.

### File List

**Modified (8)**
- `src/django_service/views.py` — `_heading_lines` removed (no callers)
- `src/django_service/templates/landing.html` — comment corrected
- `tests/unit/{test_ui_shell,test_landing_page,test_distribution_identity}.py` — read from settings
- `tests/unit/test_documentation_accuracy.py` — `as_posix()`
- `tests/unit/test_cross_platform_portability.py` — the new guard
- `tests/unit/{test_job_status_rename,test_users_api_error_envelopes,test_open_access,test_org_switcher_retirement}.py`
  — converted to `as_posix()`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Fixed the suite after the product was renamed to PyFABRIC. Five tests pinned the name's literal value, which undid Story 21.3's whole point — they now assert properties read from settings. Also fixed a Windows-only failure in the docs nav check, which compared `str(path.relative_to(...))` against forward-slash paths from `mkdocs.yml`; a new guard bans that pattern across the suite and found five more instances on its first run. |
