# Story 5.4: Licenses Tab

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want packages grouped by license risk tier,
so that I can focus on the licenses that need legal attention.

## Acceptance Criteria

1. Given a job with license data, when I view the Licenses tab, then packages are grouped into four tiers displayed in order: Strong Copyleft (Attention Required), Weak Copyleft (Review Recommended), Unknown, Permissive.
2. Given each package row, when it renders, then the package name links to its PyPI page.
3. Given a tier with zero packages, when the tab renders, then that tier is collapsed by default.
4. Given the license phase failed, when I view the tab, then a failure notice with the reason is shown.

## Tasks / Subtasks

- [ ] Task 1 — Fetch report (AC: #1)
  - [ ] Call `api/reports.getLicenses(taskId)` → `GET /api/v1/sbom/result/{taskId}/reports/licenses/` (JSON)
  - [ ] Type the response: packages grouped by tier (`strong_copyleft` / `weak_copyleft` / `unknown` / `permissive`), each with name, version, license id
- [ ] Task 2 — Tiered grouping UI (AC: #1)
  - [ ] Render four MUI accordion/section groups in fixed order: Strong Copyleft (Attention Required) → Weak Copyleft (Review Recommended) → Unknown → Permissive
  - [ ] Label each tier with its attention signal
- [ ] Task 3 — PyPI links (AC: #2)
  - [ ] Each package name links to `https://pypi.org/project/{name}/` (new tab)
- [ ] Task 4 — Collapse empty tiers (AC: #3)
  - [ ] Tiers with zero packages render collapsed by default (still visible, but not expanded)
- [ ] Task 5 — Failure notice (AC: #4)
  - [ ] If the license report `failed`, render the shared `TabFailureNotice` with `failure_reason`
- [ ] Task 6 — Tests (AC: #1, #3, #4)
  - [ ] Tiers render in the required order
  - [ ] An empty tier is collapsed by default; a populated tier is expanded
  - [ ] Failed report renders the failure notice

## Dev Notes

### Four-tier model (solution-design.md §3.4 licence service; FR-5.2)

| Tier | Examples | Signal |
|---|---|---|
| Strong Copyleft | AGPL, GPL | Attention required |
| Weak Copyleft | LGPL (MPL per design) | Review recommended |
| Unknown | no SPDX id / non-SPDX | Legal review needed |
| Permissive | MIT, Apache-2.0, BSD, ISC | Use freely |

Display order is descending attention: Strong → Weak → Unknown → Permissive. The report is produced by Epic 4 Story 4.3 and served at `GET /api/v1/sbom/result/{taskId}/reports/licenses/`. [Source: solution-design.md §3.4; epics.md#Story 4.3, #Story 5.4]

### Conventions

- Fetch via `frontend/src/api/reports.ts` — no `fetch` in the component (AD-5).
- MUI 9.1.2 accordion/list components for the collapsible tiers. [Source: solution-design.md §7.1]

### Dependency / sequencing

Depends on Story 5.1 (shell + api layer) and consumes the Epic 4 Story 4.3 licence endpoint. Independent of other tabs. [Source: epics.md#Epic 5]

### Project Structure Notes

- Licenses tab panel under `frontend/src/pages/`/`components/`; fetcher in `frontend/src/api/reports.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.4: Licenses Tab]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA: REST API only]
- [Source: solution-design.md#3.4 analysis/ — Licence service]
- [Source: solution-design.md#5.2 Endpoint inventory]
- [Source: prd.md#FR-6.4, FR-5.2, FR-6.7]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- **Frontend-only:** the license endpoint already serves inline JSON (Story 5.3). `LicensesTab` fetches `getLicenses` and renders the backend's ordered `tiers` (Strong Copyleft → Weak Copyleft → Unknown → Permissive) as MUI accordions, each labeled with its attention signal (Attention required / Review recommended / Legal review needed / Use freely) and package count.
- **Collapse (AC #3):** each accordion `defaultExpanded={packages.length > 0}` — empty tiers start collapsed, populated ones expanded.
- **PyPI links (AC #2):** each package name links to `https://pypi.org/project/{name}/` (new tab). Used a unicode `▾` expand icon to avoid adding `@mui/icons-material`.
- **Failure notice (AC #4):** shared `TabFailureNotice` on `report_failed`.
- Wired into `ResultsPage` (tab index 2). Lazy-mounted via the shell.
- **Tests:** tier order, empty-collapsed / populated-expanded, PyPI links, failure notice.
- Gate: `pixi run ci` exits 0 — backend 177 tests, frontend 16 tests.

### File List

- frontend/src/components/LicensesTab.tsx (new) + LicensesTab.test.tsx (new)
- frontend/src/pages/ResultsPage.tsx (wires the Licenses tab)
