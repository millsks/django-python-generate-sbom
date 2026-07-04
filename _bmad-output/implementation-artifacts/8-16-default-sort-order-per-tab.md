# Story 8.16: Default Sort Order Per Tab

Status: done

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- **Version Currency** default changed from currency/desc to **name/asc** (`orderBy='name'`, `order='asc'`); column-header sorting still overrides.
- **Licenses** tab (tier-grouped accordions): tiers now render in **risk order** via `TIER_RANK` (Strong Copyleft → Weak Copyleft → Unknown → Permissive) regardless of backend order, and packages within a tier are sorted by name.
- **SBOM viewer** (name/asc) and **Vulnerabilities** (severity, Critical first) were already correct — confirmed and locked with tests.
- **Tests:** Versions name-asc default (+ Status-click override now sorts status/desc); Licenses shuffled-input → risk order + within-tier name sort; SBOM name-asc default assertion; Vulns severity default already tested.
- Gate: `pixi run ci` exits 0 — backend 262, frontend 74.

### File List

- frontend/src/components/VersionsTab.tsx (default orderBy/order) + VersionsTab.test.tsx
- frontend/src/components/LicensesTab.tsx (TIER_RANK ordering + within-tier name sort) + LicensesTab.test.tsx
- frontend/src/components/SbomTab.test.tsx (name-asc default assertion)

## Story

As a user,
I want each results tab to open pre-sorted in the most useful order,
so that the rows I care about are at the top without me sorting first.

## Acceptance Criteria

1. Given the **SBOM** viewer's component table, when it opens, then it is sorted by **package name** (ascending) by default (FR-E11). *(Already the case — confirm and lock with a test.)*
2. Given the **Version Currency** tab, when it opens, then it is sorted by **package name** (ascending) by default — changed from the current "most-outdated first" default.
3. Given the **Vulnerabilities** tab, when it opens, then it remains sorted by **severity** (Critical first) by default. *(Already the case — confirm.)*
4. Given the **Licenses** tab (which groups packages into per-tier accordions, not a flat table), when it opens, then the tier groups are **ordered by risk** (copyleft → unknown → permissive) and packages within a tier are ordered by package name.
5. Given any tab, when I click a column header, then user sorting still works and overrides the default (defaults set only the initial state).

## Tasks / Subtasks

- [ ] Task 1 — Version Currency default → name (AC: #2)
  - [ ] In `VersionsTab.tsx`, change the initial `orderBy` to the package-name column and `order` to `asc`
- [ ] Task 2 — Licenses tier-group order → risk (AC: #4)
  - [ ] In `LicensesTab.tsx`, order the tier accordions by a risk rank (copyleft → unknown → permissive) and sort packages within each tier by name (add a rank map if absent)
- [ ] Task 3 — Confirm SBOM (name) and Vulnerabilities (severity) (AC: #1, #3)
  - [ ] No behavior change; add/confirm a test asserting each tab's initial sort
- [ ] Task 4 — Tests
  - [ ] Frontend per tab: the first data row reflects the specified default; clicking a header still re-sorts (AC #5)
  - [ ] `pixi run ci` exits 0

## Dev Notes

Current defaults observed: `SbomTab` sorts by name asc (matches AC #1); `VulnerabilitiesTab` initial `orderBy = 'severity'` with a `SEVERITY_RANK` (matches AC #3); `VersionsTab` initial `orderBy = 'currency'` desc (**change to name**); `LicensesTab` (**set to risk-tier**). Defaults are only the initial `useState`; the existing `TableSortLabel` click handlers keep working. [Source: frontend/src/components/VersionsTab.tsx, VulnerabilitiesTab.tsx, LicensesTab.tsx, SbomTab.tsx]

Risk-tier order for Licenses matches the vulnerabilities "most-significant-first" pattern the user chose: `copyleft` (3) → `unknown` (2) → `permissive` (1).

### References

- [Source: frontend/src/components/VersionsTab.tsx, VulnerabilitiesTab.tsx, LicensesTab.tsx, SbomTab.tsx]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
