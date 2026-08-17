---
baseline_commit: 0cf1d72
---

# Story 21.12: Results Page Shell and Overview Tab

Status: review

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

- [x] **Task 1 — Results shell (AC: #1, #2)** — Five tabs, URL-reflected active tab, org-scoped lookup that
  404s for both wrong-org and missing.
- [x] **Task 2 — htmx tab loading (AC: #1)** — Lazy-load each tab's partial; placeholders for 21.13–21.16.
- [x] **Task 3 — Overview tab (AC: #3, #4)** — Cards from `summary_stats` only; "Unavailable" for failed
  phases; deep links; SBOM download.
- [x] **Task 4 — Purged-artifact branch (AC: #5)** — Warning + Overview only.
- [x] **Task 5 — Tests + gate (AC: #6)**.

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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **664 passed**, coverage **96.35%**; frontend **223 passed**.
- **26 new tests** in `tests/unit/test_results_page.py`; route `ui-job-tab` →
  `/results/<task_id>/tab/<tab>`.
- Tab order asserted twice: against `RESULT_TABS` and against the rendered HTML's character
  positions, so a reordering fails in two independent places.
- Cross-org vs unknown: both **404**, bodies **byte-identical** after masking the CSRF token.
- The no-artifact-read guard monkeypatches `default_storage.open`/`url` to raise; the Overview
  renders **200** with both poisoned.

### Completion Notes List

**A real bug the tests caught: the bookmarked tab did not survive.** The shell always included
`_overview.html` regardless of `?tab=`, so `/results/<id>?tab=licenses` highlighted Licenses in
the tab bar while rendering the Overview underneath. The view now resolves the active tab to a
template and the shell includes *that*, so the active tab is genuinely rendered server-side —
which is what makes a bookmarked tab work with no JavaScript at all. htmx only avoids a full
reload on subsequent clicks.

**Tab state in the URL is a small improvement, not parity.** The SPA kept the active tab in
React state and lost it on refresh, so a tab could not be shared. `hx-push-url` keeps the
address in step with the visible tab, and the server renders whatever `?tab=` asks for.

**The Overview reads `summary_stats` and nothing else, and that is enforced rather than
asserted in prose.** `test_the_overview_does_not_read_the_artifact_store` monkeypatches
`default_storage.open` and `.url` to raise, then renders the page. NFR-2.2 is the whole reason
that column exists; a future edit that reaches for a report artifact to enrich a card fails
immediately instead of quietly costing four fetches per page view.

**"Unavailable" is distinguished from zero in three ways.** A failed phase, a *missing* report,
and empty `summary_stats` all read `Unavailable` rather than `0` — because 0 asserts "no
vulnerabilities", which is a claim the system cannot make when the scan did not run (FR-6.7).
The rest of the Overview still renders in every case, and the card is styled as muted with its
deep link suppressed, so it cannot be clicked through to an empty tab.

**The download is a link, not a view.** AD-11 requires a 303 to a presigned URL with Django
never streaming artifact bytes, and that endpoint already exists at
`/api/v1/sbom/result/<task_id>/`. The Overview links straight at it rather than proxying —
adding a page-side download view would have been the easy way to break AD-11.
(The Dev Notes' known pre-existing issue stands: presigned URLs point at the internal MinIO
endpoint and are unreachable from a host browser. Not introduced here, not fixed here.)

**Purged jobs degrade rather than error (Story 7.3).** A completed job with no `result_key`
renders the retention warning, the full Overview from its retained summary, **disabled** detail
tabs, and no download. Disabling beats hiding here: it explains why the tabs are unavailable
instead of silently changing the page's shape.

**One 21.11 test changed, and it was always going to.** `test_the_results_page_renders_the_completed_view_once_terminal`
asserted the placeholder text ("This job completed") that this story replaces. It now asserts
the gate opens onto the **shell** — which is what 21.11 actually owns — with the comment
recording the handover. No other assertion changed.

**Placeholders are deliberately neutral.** The four detail tabs say "arrives in Story 21.1x"
and a test asserts none of them contains the word "error", so a partially-built branch stays
navigable rather than looking broken. That matters because the epic merges as one branch.

**Not done here.** The four detail tabs are empty (21.13–21.16), and there is no Excel export
(21.17). The SPA's Overview also offered a combined "export all" workbook built client-side
with exceljs; that becomes a server-side openpyxl export in 21.17, so it is deliberately absent
rather than half-built.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (7)**
- `src/django_apps/inventory/sbom/overview.py` — `build_metrics`, `Metric`, `UNAVAILABLE`
- `src/django_apps/inventory/templates/inventory/sbom/tabs/_overview.html`
- `.../tabs/_sbom.html`, `_vulnerabilities.html`, `_licenses.html`, `_versions.html` — neutral
  placeholders for 21.13–21.16
- `tests/unit/test_results_page.py` (26 tests)

**Modified (5)**
- `src/django_apps/inventory/sbom/pages.py` — `RESULT_TABS`, `_JobScopedView`, the rebuilt
  `JobResultsView`, `JobTabPartialView`, `_resolve_tab`, `_tab_template`
- `src/django_apps/inventory/templates/inventory/sbom/results.html` — the five-tab shell
- `src/django_apps/inventory/urls_pages.py` — `ui-job-tab`
- `tests/unit/test_job_polling.py` — the 21.11 handover assertion
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Built the five-tab results shell in the SPA's order at the shareable `/results/<task_id>`, with the active tab in the URL and rendered server-side so a bookmark survives a refresh without JavaScript. The Overview renders from `summary_stats` alone — enforced by a test that makes artifact storage raise — with "Unavailable" rather than 0 for a failed or missing phase, deep links into each detail tab, and a download that links at the existing presigned-redirect endpoint rather than proxying it. Purged jobs degrade to warning-plus-Overview with disabled tabs. Cross-org and unknown tasks return byte-identical 404s. `pixi run ci` exit 0; 664 backend tests at 96.35%. |
