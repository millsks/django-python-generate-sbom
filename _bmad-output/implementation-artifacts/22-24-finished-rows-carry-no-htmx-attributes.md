---
baseline_commit: cf52b3c
---

# Story 22.24: Stop a Finished Job Row Loading the Page Into Itself

Status: review

> **This is a bug fix, so the commit type is `fix:`** (global standards §5). Reported by the product owner:
> *"whenever I click on a line in the Job Status page (not the view link) it miscombobulates the view. It
> seems like it is trying to load the job status view inside of the job status view."* — which is exactly
> what it was doing.

## Story

As someone browsing Job Status,
I want clicking a row to do nothing,
so that the page does not load a copy of itself into its own table.

**Context:** `poll_attrs` returns `{}` for a terminal job, and the intent — since Story 21.11 — was that a
finished row issues no requests at all. But the row rendered `hx-get="" hx-trigger="" hx-swap=""`: the
attributes were **present and blank**, because `row_attrs` used `.get(attr, "")`.

htmx reads that difference as an instruction. An empty `hx-get` means *GET the current URL*, a `<tr>`'s
default trigger is a **click**, and the default swap is `innerHTML` — so clicking a finished row fetched
`/job-status` and swapped the entire page, nav and footer included, into the row.

## Acceptance Criteria

1. **A terminal row carries no `hx-` attributes at all**, not merely empty ones.
2. **A running row still carries all three**, and its `hx-get` is never blank.
3. **No row on the rendered page** has a blank htmx attribute.
4. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Write the failing tests first (AC: #1, #3)**
- [x] **Task 2 — `.get(attr)` instead of `.get(attr, "")` (AC: #1, #2)**
- [x] **Task 3 — Verify against the rendered page, not only the partial (AC: #3)**
- [x] **Task 4 — Gate (AC: #4)**

## Dev Notes

### Why the one-character fix is the right one

`django_tables2.utils.AttributeDict._iteritems` filters on `value is not None`. A `None` is omitted; an
empty string is rendered as a blank attribute. The intent was already expressed correctly in `poll_attrs`
— it returns an empty dict — and only the `row_attrs` default undid it.

### Traps

- **Empty is not absent.** This is the general lesson: for any attribute-driven library, rendering
  `attr=""` is a statement, not a blank. htmx, `aria-*`, and `download` all read it that way.
- **The bug is invisible in the partial's happy path.** A running row looks right, and a finished row looks
  right too unless you read its attributes or click it. The assertion is "no `hx-` at all" rather than "no
  `hx-get`", because the same mistake in any of the three produces the same class of surprise.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- Rendered a finished row before the fix: `<tr id="job-row-…" hx-get="" hx-trigger="" hx-swap="" class="even">`.
  After: `<tr id="job-row-…" class="even">`.
- 3 new tests in `tests/unit/test_job_polling.py`; 2 failed before the fix.
- `pixi run ci` — **exit 0**, 1078 tests, 97.25%.

### Completion Notes List

**The screenshot named the cause.** "Trying to load the job status view inside of the job status view" is
literally what an empty `hx-get` on a clickable element does, and reading it that way found the attribute
in one step rather than a search through the polling logic.

**Nothing tested the finished row's markup.** Story 21.11's tests asserted that a running row polls and that
a finished row *stops* polling — both true, and neither looked at what a finished row actually renders.
Behaviour that happens on click was never exercised because nothing clicked.

**A gate failure that was mine, not the code's.** The first `pixi run ci` after this fix failed on
`test_default_sqlite_path_resolves_under_the_repository_root` — a `DATABASE_URL` left exported by the
diagnostic command in the same shell. Re-run clean, it passes. Worth recording so the next reader does not
treat it as flaky.

### File List

**Modified (2)**
- `src/django_apps/inventory/sbom/tables.py` — `.get(attr)` rather than `.get(attr, "")`, with the reason
- `tests/unit/test_job_polling.py` — 3 tests

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Fixed clicking a finished Job Status row loading the whole page into its own table. `row_attrs` defaulted the polling attributes to `""` rather than omitting them, and django-tables2 renders a blank attribute where it omits a `None` — so a terminal row carried `hx-get=""`, which htmx reads as "GET the current URL" on click. The intent was already right in `poll_attrs`; only the default undid it. |
