# Story 5.2: Overview Tab

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want an overview of my SBOM results with a download button,
so that I can grasp the summary at a glance and retrieve the SBOM.

## Acceptance Criteria

1. Given a completed job, when I view the Overview tab, then it shows total package count, vulnerable package count, license category breakdown (permissive / copyleft / unknown), and package counts at current / behind / unknown versions.
2. Given the Overview tab, when I click the SBOM download button, then the SBOM artifact downloads in the format submitted at job creation, via the `303`-to-presigned-URL flow.
3. Given the Overview summary cards, when I click a category (e.g., vulnerable packages), then I am linked to the corresponding analysis tab.
4. Given an Overview summary metric backed by a failed analysis phase, when the tab renders, then that metric indicates the data is unavailable rather than showing a misleading zero.

## Tasks / Subtasks

- [ ] Task 1 — Summary source (AC: #1)
  - [ ] Read the job `summary_stats` (from `GET /api/v1/sbom/status/{taskId}/` result / job detail) via `api/jobs.ts` — total packages, vulnerable count, license-tier breakdown, version-currency counts
  - [ ] Where a metric is derived from a specific report, prefer the job `summary_stats` populated at persist (Phase 8) so Overview needs no per-report fetch for the counts (keeps NFR-2.2 <3s)
- [ ] Task 2 — Summary cards UI (AC: #1)
  - [ ] Render MUI cards: total package count; vulnerable package count; license breakdown (permissive / copyleft / unknown); versions at current / behind / unknown
  - [ ] Layout must render within the <3s budget (NFR-2.2) — no heavy graph work on this tab
- [ ] Task 3 — SBOM download button (AC: #2)
  - [ ] Wire to `api/jobs.downloadSbom(taskId)` which hits `GET /api/v1/sbom/result/{taskId}/` → follows the `303` to the presigned S3/MinIO URL (AD-11)
  - [ ] Filename/format reflects the `output_format` submitted at creation (`cdx-json`/`cdx-xml`/`spdx-2.3`)
  - [ ] Disable the button if artifacts are unavailable (expired — Epic 7) with a tooltip
- [ ] Task 4 — Category deep-links (AC: #3)
  - [ ] Clicking the vulnerable-packages card switches to the Vulnerabilities tab; license card → Licenses tab; version card → Version Currency tab (drive the shell's active-tab state from 5.1)
- [ ] Task 5 — Failed-phase handling (AC: #4)
  - [ ] For any metric whose backing report `failed`, render "unavailable" (not `0`) — reuse the availability flags from the 5.1 page state
- [ ] Task 6 — Tests (AC: #1, #2, #4)
  - [ ] Component test: cards show the four metric groups from a sample summary
  - [ ] Component test: download button invokes the api download function
  - [ ] Component test: a failed report renders "unavailable" rather than 0

## Dev Notes

### Prefer job summary_stats over per-report fetches (NFR-2.2)

`SBOMJob.summary_stats` is populated at Phase 8 persist with `{total_packages, direct, transitive, vulnerability_count, ...}` and per-tier / per-currency counts. Sourcing Overview from `summary_stats` avoids four report round-trips and keeps the tab within the <3s load budget. [Source: solution-design.md §3.3 SBOMJob.summary_stats, §4.2 phase 8]

### Download flow (AD-11; solution-design.md §6.2)

`GET /api/v1/sbom/result/{taskId}/` returns `303 See Other` → presigned S3/MinIO URL (24h TTL). Django never proxies bytes. The api-layer helper should let the browser follow the redirect to trigger the download. [Source: ARCHITECTURE-SPINE.md AD-11; solution-design.md §6.2]

### Deep-linking to tabs

The five-tab active state lives in the 5.1 `ResultsPage` shell. Overview cards set the active tab index rather than navigating routes (the URL stays `/results/:taskId`). [Source: epics.md#Story 5.2]

### Failed-phase handling (FR-6.7)

Uses the availability flags computed in 5.1. A failed report → "unavailable", never a misleading `0`. [Source: epics.md#Story 5.2]

### Dependency / sequencing

Depends on Story 5.1 (shell + page state + api layer). Consumes job `summary_stats` (produced by Epic 3 Phase 8) and the SBOM download endpoint (Epic 3). Independent of the other tabs. [Source: epics.md#Epic 5]

### Project Structure Notes

- Overview implemented as a tab panel component under `frontend/src/pages/` (or `frontend/src/components/` if factored out); download helper in `frontend/src/api/jobs.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2: Overview Tab]
- [Source: ARCHITECTURE-SPINE.md#AD-11 — Artifact downloads via presigned URL]
- [Source: solution-design.md#3.3 sbom/ — SBOMJob.summary_stats]
- [Source: solution-design.md#6.2 Presigned URL download flow]
- [Source: prd.md#FR-6.2, FR-6.7, NFR-2.2]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- **Backend — summary source (NFR-2.2):** `services.record_analysis_summaries(task_id, envelopes)` merges the four report summaries into `SBOMJob.summary_stats["reports"]` at the aggregate callback (counts + `failed`/`failure_reason`; the graph's `nodes`/`edges` lists are stripped to avoid DB bloat). The status endpoint now returns `summary_stats` + `output_format`, so Overview needs **no per-report fetch**.
- **`OverviewTab`** (new component): metric cards sourced entirely from `summary_stats` — total packages; vulnerabilities; license breakdown (permissive / copyleft [strong+weak] / unknown); version currency (current / behind [behind-1 + behind-2+] / unknown). A **SBOM download** button (303-to-presigned flow, labels the `output_format`).
- **Deep-links (AC #3):** clicking the Vulnerabilities/Licenses/Version cards drives the shell's active-tab state via `onNavigate` (`ResultsPage` passes `setTab`) — the URL stays `/results/:taskId`.
- **Failed-phase handling (AC #4):** a metric whose backing report `failed` renders **"Unavailable"**, never a misleading `0`.
- **Tests:** backend — aggregate merges summaries + strips graph lists; frontend — the four metric groups render, the download link reflects the format, a failed report shows "Unavailable", and a card deep-links to its tab.
- Gate: `pixi run ci` exits 0 — backend 177 tests (95.39%), frontend 8 tests.

### File List

- backend/generate_sbom/sbom/services.py (record_analysis_summaries)
- backend/generate_sbom/tasks/sbom_pipeline.py (aggregate calls it)
- backend/generate_sbom/sbom/views.py (status returns summary_stats + output_format)
- backend/tests/unit/test_pipeline_orchestration.py, tests/integration/test_pipeline_orchestration.py (updated)
- frontend/src/components/OverviewTab.tsx (new) + OverviewTab.test.tsx (new)
- frontend/src/pages/ResultsPage.tsx (wires OverviewTab), src/api/jobs.ts (SummaryStats types)
