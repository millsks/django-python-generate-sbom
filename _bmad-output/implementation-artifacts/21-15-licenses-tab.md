# Story 21.15: Licenses Tab

Status: ready-for-dev

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

- [ ] **Task 1 — Tier rendering (AC: #1, #2)** — Four collapsible sections in backend order; counts; empty
  tiers collapsed.
- [ ] **Task 2 — Expand/collapse-all (AC: #3)** — Minimal vanilla JS or Bootstrap collapse API.
- [ ] **Task 3 — Failure notice reuse (AC: #4)**.
- [ ] **Task 4 — Tests + gate (AC: #5)**.

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

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
