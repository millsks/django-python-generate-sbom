# Story 8.17: Expand All / Collapse All on the Licenses Tab

Status: review

## Story

As a user,
I want "Expand all" and "Collapse all" buttons on the Licenses tab,
so that I can open or close every risk-tier group at once instead of clicking each accordion.

## Acceptance Criteria

1. Given the Licenses tab, when it renders, then "Expand all" and "Collapse all" controls appear above the tier accordions (FR-E12).
2. Given I click "Expand all", when it fires, then every tier accordion opens.
3. Given I click "Collapse all", when it fires, then every tier accordion closes.
4. Given I toggle an individual accordion, when I do, then it opens/closes independently, and the Expand/Collapse-all controls still act on all groups on their next click.
5. Given a failed/empty license report, when the tab renders, then the controls are hidden/disabled (nothing to expand).

## Tasks / Subtasks

- [ ] Task 1 — Controlled accordions (AC: #2, #3, #4)
  - [ ] Lift the per-tier expanded state into `LicensesTab` (a `Set`/record of expanded tier keys), initialized to the current default (tiers with packages expanded); make each `Accordion` controlled via `expanded` + `onChange`
- [ ] Task 2 — Expand/Collapse all controls (AC: #1, #5)
  - [ ] Add two buttons above the accordions; "Expand all" sets all tier keys expanded, "Collapse all" clears them; hide/disable when the report failed or has no tiers
- [ ] Task 3 — Tests
  - [ ] Frontend: Expand all opens every accordion; Collapse all closes them; an individual toggle still works; controls hidden on failure/empty
  - [ ] `pixi run ci` exits 0

## Dev Notes

`LicensesTab` currently renders one MUI `Accordion` per legal-risk tier, each **uncontrolled** (`defaultExpanded={tier.packages.length > 0}`). This story makes them **controlled** (expanded state in the component) so the two buttons can drive them together while individual toggles still work. [Source: frontend/src/components/LicensesTab.tsx]

Coordinates with Story 8.16 (licenses default order = tier groups copyleft-first): the initial expanded set should still follow the "tiers with packages expanded" rule regardless of group order.

### References

- [Source: frontend/src/components/LicensesTab.tsx]
- [Source: _bmad-output/implementation-artifacts/8-16-default-sort-order-per-tab.md]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

- `pixi run ci` → exit 0 (backend: 242 passed, 93.95% coverage; frontend: 58 passed across 12 files, build OK).

### Completion Notes List

- Lifted the per-tier expanded state into `LicensesTab` as a `Set<string>` of expanded tier keys, populated on report load with the existing default ("tiers with packages expanded"). Tier group order is untouched (owned by Story 8.16).
- Converted each `Accordion` from uncontrolled (`defaultExpanded`) to controlled (`expanded` + `onChange`); the per-tier `onChange` adds/removes that tier's key so individual toggles remain independent.
- Added "Expand all" / "Collapse all" MUI buttons in a `Stack` above the accordions. Expand-all sets every tier key; Collapse-all clears the set. The control row is rendered only when `report.tiers.length > 0`, so it is absent on the empty report and on the failure path (which returns the shared `TabFailureNotice` before reaching the controls).
- Added 5 tests: expand-all opens every accordion, collapse-all closes every accordion, an individual toggle acts independently and expand-all still drives all groups afterward, and the controls are hidden on both the empty-report and failed-report paths.

### File List

- frontend/src/components/LicensesTab.tsx (modified)
- frontend/src/components/LicensesTab.test.tsx (modified)
