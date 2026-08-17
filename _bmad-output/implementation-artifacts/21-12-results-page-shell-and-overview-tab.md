# Story 21.12: Results Page Shell and Overview Tab

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.11**. Builds the five-tab shell; the four detail tabs are **placeholders
> until Stories 21.13–21.16 fill them**. That is acceptable because the SPA remains mounted for the whole epic
> (big-bang branch) and is only removed in 21.19.

## Story

As a user,
I want a shareable results page with an Overview of my SBOM job,
so that I can see summary metrics and reach the detail views.

## Acceptance Criteria

1. **The five-tab shell is converted.**
   Given `ResultsPage.tsx:26-32` declares five tabs in the order **Overview, SBOM, Vulnerabilities, Licenses,
   Version Currency**, when the shell is converted, then the same five tabs render in the same order at the
   same shareable `/results/<task_id>` URL, the active tab is reflected in the URL so a tab is bookmarkable and
   survives refresh, and tab content loads via htmx.
2. **Cross-org and unknown tasks are indistinguishable.**
   Given results are org-scoped and must not leak existence (**AD-2**), when an unauthorised user requests a
   results URL, then they receive the same response as for a non-existent task, with no difference in status
   code or body.
3. **Overview reads only `summary_stats`.**
   Given `OverviewTab.tsx` renders summary cards "sourced entirely from the job's `summary_stats` (no per-report
   fetch — NFR-2.2)", when it is converted, then the same metrics render from that same single source, each
   card deep-links to its detail tab, and the SBOM download is available.
4. **A failed phase shows "Unavailable", never a misleading zero.**
   Given FR-6.7 requires graceful degradation per phase, when a metric is backed by a failed analysis phase,
   then that metric renders **"Unavailable"** rather than `0`, and the rest of the Overview still renders.
5. **Purged artifacts degrade to summary-only.**
   Given a completed job whose artifacts were cleaned retains only its summary (Story 7.3), when its results
   page is opened, then the retention warning and the Overview render, and the detail tabs and downloads are
   unavailable rather than erroring.
6. **Gate green.**
   When the story completes, then tests cover the tab shell and ordering, tab bookmarkability, cross-org
   denial, the failed-phase metric, and the purged-artifact state, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — Results shell (AC: #1, #2)** — Five tabs, URL-reflected active tab, org-scoped lookup that
  404s for both wrong-org and missing.
- [ ] **Task 2 — htmx tab loading (AC: #1)** — Lazy-load each tab's partial; placeholders for 21.13–21.16.
- [ ] **Task 3 — Overview tab (AC: #3, #4)** — Cards from `summary_stats` only; "Unavailable" for failed
  phases; deep links; SBOM download.
- [ ] **Task 4 — Purged-artifact branch (AC: #5)** — Warning + Overview only.
- [ ] **Task 5 — Tests + gate (AC: #6)**.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/pages/ResultsPage.tsx:26-32` — the `TABS` array in order: Overview, SBOM, Vulnerabilities,
  Licenses, Version Currency. (The Dependency Graph tab was retired by Story 20.1.)
- `ResultsPage.tsx:1-3` header comment — "tabs over a completed job's outputs, with a shareable URL
  (`/results/:taskId`), org access control, and a polling gate".
- `ResultsPage.tsx:59-72` — `pageError === 'denied'` renders "You don't have access to these results, or they
  don't exist" — one message for both cases, deliberately.
- `ResultsPage.tsx:97-112` — the `SUCCESS && !artifacts_available` branch renders a warning plus the Overview
  only.
- `frontend/src/components/OverviewTab.tsx:1-4` header comment — "summary cards sourced entirely from the
  job's `summary_stats` (no per-report fetch — NFR-2.2) … A metric backed by a failed phase shows 'Unavailable'
  rather than a misleading 0 (FR-6.7)."
- Overview deep-links into tabs by index via an `onNavigate` callback; the server-rendered equivalent links by
  tab name in the URL.

### Why the Overview must not fetch reports

NFR-2.2 (UI load time) is the reason `summary_stats` exists on the job. Fetching four report artifacts to
render summary cards would reintroduce exactly the cost that design avoided. Keep it to the single source.

### Placeholder tabs are expected here

Stories 21.13–21.16 fill them. A placeholder must render a neutral "loading"/"not yet available" state, never
an error, so that a partially-built branch is still navigable.

### Watch for

- **Tab state in the URL** is what makes a tab shareable — the SPA held it in React state and lost it on
  refresh, so this is a small improvement, not a regression.
- **The download must remain a presigned redirect** (**AD-11**: `303 See Other` to a presigned URL, Django
  never streams artifact bytes). Do not proxy it through the view.
- Presigned URLs currently point at the internal MinIO endpoint, which is unreachable from a host browser —
  a known pre-existing issue, not introduced here, but it will be visible when testing downloads locally.

### Testing standards

- A test asserting the tab order matches the SPA's exactly.
- A test asserting the wrong-org and missing-task responses are byte-identical.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.12: Results Page Shell and Overview Tab]
- `frontend/src/pages/ResultsPage.tsx`, `frontend/src/components/OverviewTab.tsx`,
  `generate_sbom/{sbom,analysis}/{views,selectors}.py`.
- Upstream: `21-11-live-job-progress-via-htmx-polling.md`. Downstream: `21-13` … `21-17`.
- Architecture: AD-2 (org isolation), AD-11 (presigned downloads), NFR-2.2, FR-6.7.

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
