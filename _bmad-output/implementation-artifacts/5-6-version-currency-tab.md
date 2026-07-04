# Story 5.6: Version Currency Tab

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a sortable table of package version currency,
so that I can see which dependencies are outdated and by how much.

## Acceptance Criteria

1. Given a job with version currency data, when I view the Version Currency tab, then a table lists all packages with installed version, latest version, and a currency status badge (Current / Behind / Unknown).
2. Given the version currency table, when it first loads, then packages classified `behind-2+` are displayed first by default.
3. Given the version currency table, when I sort by status, then rows reorder by currency status.
4. Given the version currency phase failed, when I view the tab, then a failure notice with the reason is shown.

## Tasks / Subtasks

- [ ] Task 1 — Fetch report (AC: #1)
  - [ ] Call `api/reports.getVersions(taskId)` → `GET /api/v1/sbom/result/{taskId}/reports/versions/` (JSON)
  - [ ] Type the response: per-package entries with name, installed version, latest version, currency classification (`current` / `behind-1` / `behind-2+` / `unknown`)
- [ ] Task 2 — Table UI + badges (AC: #1)
  - [ ] MUI table: package, installed version, latest version, currency status badge
  - [ ] Map classifications to display badges: Current (`current`), Behind (`behind-1` / `behind-2+`), Unknown (`unknown`) — keep the finer class available for sort ordering
- [ ] Task 3 — Default ordering (AC: #2)
  - [ ] On first load, order so `behind-2+` rows appear first (most-outdated surfaced), then `behind-1`, then `current`/`unknown`
- [ ] Task 4 — Sort by status (AC: #3)
  - [ ] Column sort by currency status reorders rows by class rank
- [ ] Task 5 — Failure notice (AC: #4)
  - [ ] If the version report `failed`, render the shared `TabFailureNotice` with `failure_reason`
- [ ] Task 6 — Tests (AC: #2, #3, #4)
  - [ ] Default ordering puts `behind-2+` first
  - [ ] Sorting by status reorders by class rank
  - [ ] Failed report renders the failure notice

## Dev Notes

### Currency classification (solution-design.md §3.4 version service; FR-5.4)

Latest stable fetched from the PyPI JSON API; installed vs latest compared by PEP 440 release-series distance. Classes: `current` (same series), `behind-1` (one series behind), `behind-2+` (two+ series behind, incl. major gaps), `unknown` (no data). LTS-aware for Django/Python via `SBOM_LTS_REGISTRY`. Report produced by Epic 4 Story 4.5, served at `GET /api/v1/sbom/result/{taskId}/reports/versions/`. Display badge collapses to Current/Behind/Unknown while the underlying class drives ordering. [Source: solution-design.md §3.4; epics.md#Story 4.5, #Story 5.6]

### Conventions

- Fetch via `frontend/src/api/reports.ts` — no `fetch` in the component (AD-5).
- MUI 9.1.2 table + chip/badge components. [Source: solution-design.md §7.1]

### Dependency / sequencing

Depends on Story 5.1 (shell + api layer) and consumes the Epic 4 Story 4.5 version endpoint. Independent of other tabs. [Source: epics.md#Epic 5]

### Project Structure Notes

- Version Currency tab panel under `frontend/src/pages/`/`components/`; fetcher in `frontend/src/api/reports.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.6: Version Currency Tab]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA: REST API only]
- [Source: solution-design.md#3.4 analysis/ — Version currency service]
- [Source: solution-design.md#5.2 Endpoint inventory]
- [Source: prd.md#FR-6.6, FR-5.4, FR-6.7]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- **`VersionsTab`** (new, frontend-only — the versions endpoint already serves inline JSON): MUI table of package, installed, latest, and a **status badge** (MUI `Chip`) — Current (green), Behind 1 / Behind 2+ (orange), Unknown (grey). The badge collapses the four classes to Current/Behind/Unknown while the underlying class drives ordering.
- **Default ordering (AC #2):** sorted by currency **class rank** descending — `behind-2+` first, then `behind-1`, `current`, `unknown` — so the most-outdated packages surface at the top.
- **Sort by status (AC #3):** clicking the Status header toggles asc/desc by class rank; other columns sort lexically.
- **Failure notice (AC #4):** shared `TabFailureNotice` on `report_failed`; empty state on no data.
- Wired into `ResultsPage` (tab index 4). **This completes all five result tabs** (with 5.7 theme already done, Epic 5 is finished).
- **Tests:** default behind-2+-first ordering, status-sort reorder, failure notice.
- Gate: `pixi run ci` exits 0 — backend 177 tests, frontend 22 tests.

### File List

- frontend/src/components/VersionsTab.tsx (new) + VersionsTab.test.tsx (new)
- frontend/src/pages/ResultsPage.tsx (wires the Version Currency tab — all five panels now live)
