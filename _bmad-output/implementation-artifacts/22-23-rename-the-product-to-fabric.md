---
baseline_commit: 899bc65
---

# Story 22.23: Rename the Product to FABRIC

Status: review

> **Product-owner direction:** *"Update the top bar from Supply Lens to FABRIC … replace the Python
> Inventory Supply Lens to the acronym FABRIC without any dots and work in the full name Framework for
> Automated Bill of Materials & Risk Inventory in Code."* Refined twice while building: the expansion came
> **out** of the top bar again, and the landing heading was shrunk and broken after the ampersand.

## Story

As the product owner,
I want the application to be called FABRIC,
so that its name says what it does.

**Context:** The product was **Python Inventory Supply Lens** ("Supply Lens"). Story 21.3 made the name a
single definition in settings, reaching templates through a context processor, with a test forbidding a
literal in markup — which is what made this rename two lines of configuration rather than a search and
replace.

## Acceptance Criteria

1. **`PRODUCT_NAME` / `PRODUCT_NAME_SHORT` carry the new names**, the acronym written without dots.
2. **The top bar shows the acronym alone.**
3. **The landing heading spells the name out**, at a smaller size, broken after the ampersand.
4. **The docs and README follow**, and the distribution name does **not**.
5. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — The two settings, with the reason recorded beside them (AC: #1)**
- [x] **Task 2 — Top bar: acronym only (AC: #2)**
- [x] **Task 3 — Landing heading: `h2`, split after the ampersand by the view (AC: #3)**
- [x] **Task 4 — README, `docs/index.md`, the section indexes, `mkdocs.yml` (AC: #4)**
- [x] **Task 5 — Update the tests that pin the name; guard the new rules (AC: all)**
- [x] **Task 6 — Gate (AC: #5)**

## Dev Notes

### Why the line break is computed in the view

Putting a `<br>` in `PRODUCT_NAME` would have been quickest and is wrong: that same string is the `<title>`
and the footer, where markup is escaped and would be shown literally. Leaving the break to the browser is
also wrong — the wrap point moves with the viewport, and the name reads as two halves. `_heading_lines`
partitions on the ampersand and returns a single line when there is none, so a future rename cannot produce
an empty second line.

### What deliberately did not change

The **distribution** is still `python-inventory-supply-lens`, and the repository is still
`django-python-generate-sbom`. Story 21.22 established that the product name and the distribution identity
are separate things; renaming the latter breaks existing links and discards the SonarCloud history. The
README says so in place.

`docs/developer/rename-audit.md` is untouched: it is frozen evidence for the *previous* rename (Story 22.22),
and rewriting it to describe this one would destroy the record.

### Two things the tests said

- **A guard that was too strict.** `test_no_template_hardcodes_the_product_name` fired on a `{% comment %}`
  explaining the new brand. A comment never reaches the rendered page, so the check now strips
  `{% comment %}` blocks — while deliberately still checking `{# … #}`, which has no DOTALL in Django's
  lexer and does leak.
- **A test that was too clever, and wrong.** A check that the short name is the long name's acronym failed:
  the expansion spells **FABMRIC**. It is a backronym, which is normal and fine; the test asserted a
  constraint nobody had agreed to. Deleted rather than contorted.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run docs-build` — clean. `pixi run ci` — **exit 0**, 1075 tests, 97.25%.
- New guards: the bar carries the acronym and **not** the expansion; the acronym has no dots; the heading
  breaks after the ampersand and is not display-sized.

### Completion Notes List

**Story 21.3's rule paid for itself.** The name being a single definition, with a test forbidding literals in
templates, is why this was a settings change rather than an archaeology exercise. Worth remembering the next
time that rule looks like ceremony.

**The direction changed twice mid-build, and both changes were right.** The expansion under the acronym in
the top bar crowded the chrome without earning the space, and the landing heading at `display-5` pushed the
page's content below the fold once the name got long. Both are recorded in the template comments so the next
person does not re-try them.

### File List

**Modified (10)**
- `src/config/settings/base.py` — the two names
- `src/django_service/views.py` — `_heading_lines`
- `src/django_service/templates/{base,landing}.html`
- `README.md`, `docs/index.md`, `docs/{developer,user-guide}/index.md`,
  `docs/deployment/openshift/index.md`, `mkdocs.yml`
- `tests/unit/{test_ui_shell,test_landing_page,test_distribution_identity}.py`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Renamed the product to **FABRIC** — *Framework for Automated Bill of Materials & Risk Inventory in Code* — written without dots. Two settings lines carried the rename, because Story 21.3 made the name a single definition and forbade literals in templates. The top bar shows the acronym alone; the landing page spells it out at `h2` with a break after the ampersand, computed in the view so the same string can still serve the `<title>` and footer unescaped. The distribution and repository names are deliberately unchanged. |
