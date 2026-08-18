---
baseline_commit: 5184696
---

# Story 21.15: Licenses Tab

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.14**. Reuses the shared failure-notice partial that story built.

## Story

As a user,
I want packages grouped into legal-risk tiers,
so that I can assess licence compliance at a glance.

## Acceptance Criteria

1. **The four tiers are converted in order.**
   Given `LicensesTab.tsx` groups packages into four legal-risk tiers "in the backend's descending-attention
   order" (Story 5.4), when it is converted, then the same four tiers render in the same backend-supplied
   order, each as a collapsible section, with the same per-tier counts.
2. **Empty tiers start collapsed.**
   Given the SPA renders each tier as an accordion that "starts collapsed when empty", when the tab renders,
   then empty tiers are collapsed and non-empty tiers follow the existing default.
3. **Expand-all / collapse-all works across all four.**
   Given Story 8.17 added expand/collapse-all, when it is converted, then a single control expands or
   collapses all four tiers.
4. **A failed phase shows the shared notice.**
   Given the licence phase can fail independently (FR-6.7), when it has failed, then the tab shows the shared
   failure notice from Story 21.14 with its recorded reason.
5. **Gate green.**
   When the story completes, then tests cover tier ordering, per-tier membership, empty-tier collapse,
   expand/collapse-all, and the failed-phase notice, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [x] **Task 1 — Tier rendering (AC: #1, #2)** — Four collapsible sections in backend order; counts; empty
  tiers collapsed.
- [x] **Task 2 — Expand/collapse-all (AC: #3)** — Minimal vanilla JS or Bootstrap collapse API.
- [x] **Task 3 — Failure notice reuse (AC: #4)**.
- [x] **Task 4 — Tests + gate (AC: #5)**.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/components/LicensesTab.tsx:1-3` header comment — "packages grouped into four legal-risk tiers
  (in the backend's descending-attention order), each an accordion that starts collapsed when empty. A failed
  phase shows the shared `TabFailureNotice`."
- Uses MUI `Accordion`/`AccordionSummary`/`AccordionDetails` — replaced by Bootstrap collapse or native
  `<details>`.
- The four-tier classification is produced by `generate_sbom/analysis/services/license.py` (Story 4.3); the
  tab **does not** compute or reorder tiers.
- Story 8.17 added expand/collapse-all; Story 8.25 wrote licences into the SBOM document itself, which is why
  the SBOM tab's Licence column stopped showing "—" — that is Story 21.13's concern, not this one.
- Excel export is Story 8.14 — reimplemented server-side in **Story 21.17**, not here.

### Tier order is backend-owned

The "descending attention" ordering comes from the backend service. Do not sort tiers in the template or
hardcode their names — read the order the report supplies, or a future change to the classification silently
renders in the wrong order.

### Native `<details>` is a legitimate choice

Bootstrap collapse and `<details>`/`<summary>` both satisfy the ACs. `<details>` needs no JS for the per-tier
toggle, leaving JS only for expand/collapse-all — worth preferring given the epic's low-JS goal.

### Testing standards

- A test asserting tier order matches the order in the report payload, not a hardcoded list.
- A test asserting an empty tier renders collapsed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.15: Licenses Tab]
- `frontend/src/components/{LicensesTab,TabFailureNotice}.tsx`, `frontend/src/api/reports.ts`,
  `generate_sbom/analysis/services/license.py`.
- Upstream: `21-14-vulnerabilities-tab.md`. Downstream: `21-17`.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **715 passed**, coverage **96.50%**; frontend **223 passed**.
- **15 new tests** in `tests/unit/test_licenses_tab.py`.
- Tier ordering asserted twice: once against the order the fixture supplied, and once by
  **reversing** the payload and checking the rendering reverses with it.
- Collapse state: 4 `<details>` rendered, 3 carrying `open`; with the Weak Copyleft tier
  populated, all 4 carry `open`.
- The shared notice verified by rendering it from **both** the licences and the vulnerabilities
  tab and asserting the same heading appears in each.

### Completion Notes List

**The ordering test is the one that would actually catch a hardcoded template.** Asserting
"tiers appear in the report's order" passes just as happily against a template that names the
four tiers itself, because the fixture and the hardcoded list agree. So there is a second test
that **reverses the payload's tier list** and asserts the rendering reverses too — that fails
against any template-side ordering. The Dev Notes warned that a hardcoded order renders
correctly today and silently wrongly after a classifier change; this is what makes that
detectable.

**Native `<details>`/`<summary>`, as the Dev Notes preferred.** The per-tier toggle then needs
no JavaScript at all — the tab is fully usable with JS disabled apart from the two bulk
buttons, which is a better floor than a Bootstrap-collapse implementation would have given.
Script is ~10 lines, doing only expand/collapse-all.

**Empty tiers are collapsed, not hidden.** A tier being empty is itself information ("no strong
copyleft here"), so it renders with a zero badge and an explicit "No packages in this tier."
Hiding it would silently change the shape of the page depending on the data.

**A test that guards against a coincidence.** `test_an_empty_tier_starts_collapsed_and_a_populated_one_open`
could pass for the wrong reason if the collapse logic keyed off tier *position* rather than
count, so a second fixture populates the previously-empty tier and asserts all four open.

**Two assertions initially counted the wrong things.** `html.count("<details")` returned 5, not
4, and `html.count("data-license-tier")` likewise — because the tab's own inline script mentions
`<details>` in a comment and uses `[data-license-tier]` as a selector. Both now match the full
opening tag, with the reason recorded in the test module so nobody loosens them back.

**The failure notice is genuinely reused, and there is a test proving it.** Rather than
asserting the licences tab contains some warning text, the test renders a failed licences tab
*and* a failed vulnerabilities tab and asserts the same heading appears in both — which is the
observable form of "shared partial, not copied".

**Missing and failed stay distinct here too**, on the same `read_report` three-state result that
21.14 introduced. This tab has no separate "clean" state: a licence report always carries all
four tiers, so an all-empty report is a legitimately rendered set of zero-count tiers rather
than a special case.

**Not done here.** The Excel export of this report is Story 21.17. There is no per-tier sorting
or filtering — the SPA had neither, and the tiers are the organising principle rather than a
table to slice.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (2)**
- `src/django_apps/inventory/templates/inventory/sbom/tabs/_licenses.html` — the real tab
- `tests/unit/test_licenses_tab.py` (15 tests)

**Modified (2)**
- `src/django_apps/inventory/sbom/pages.py` — `licenses_tab_context`, registered in
  `TAB_CONTEXT_BUILDERS`
- `tests/unit/test_results_page.py` — placeholder list narrowed to `versions`; the
  bookmarkable-tab test now asserts real licences content instead of the retired placeholder
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Filled in the Licenses tab: the four legal-risk tiers rendered in the order the report supplies, each a native `<details>` section that starts open when populated and collapsed when empty, with expand/collapse-all. Tier order is proven backend-owned by a test that reverses the payload and requires the rendering to reverse with it. Reuses Story 21.14's shared failure notice, verified by asserting the same heading renders from both tabs. `pixi run ci` exit 0; 715 backend tests at 96.50%. |
