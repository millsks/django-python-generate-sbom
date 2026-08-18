---
baseline_commit: 5e05912
---

# Story 21.14: Vulnerabilities Tab

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.13**. Third tab of the results shell.

## Story

As a user,
I want a sortable, severity-filterable table of vulnerable packages,
so that I can triage my dependencies' security findings.

## Acceptance Criteria

1. **The table is converted.**
   Given `VulnerabilitiesTab.tsx` renders "a sortable, severity-filterable table of vulnerable packages", when
   it is converted, then a django-tables2 table with a django-filter severity filter renders the same columns,
   the same severity ordering, and the same outbound advisory links (OSV/CVE, with the NVD CWE enrichment from
   Epic 4), with sorting and filtering carried in the querystring.
2. **The default sort is preserved.**
   Given Story 8.16 set a default sort order per tab, when the table renders with no explicit sort, then it
   matches the SPA's default.
3. **A clean scan shows an explicit zero-state.**
   Given the SPA shows "an explicit zero-state rather than an empty table", when no vulnerabilities were found,
   then the tab states that the scan found none — visibly distinct from "no data available".
4. **A failed phase shows the shared notice.**
   Given analysis phases fail independently (FR-6.7) and the SPA renders `TabFailureNotice` with the recorded
   reason, when the vulnerability phase has failed, then the tab shows the same failure notice with its reason
   instead of an empty or zero result.
5. **Gate green.**
   When the story completes, then tests cover sorting, severity filtering, the default sort, the zero-state,
   and the failed-phase notice, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [x] **Task 1 — `VulnerabilityTable` (AC: #1, #2)** — Columns, severity ordering, advisory links.
- [x] **Task 2 — Severity `FilterSet` (AC: #1)** — Querystring-driven.
- [x] **Task 3 — Zero-state vs. no-data (AC: #3)** — Two distinct states; do not collapse them.
- [x] **Task 4 — Failure notice partial (AC: #4)** — Shared with Stories 21.15 and 21.16.
- [x] **Task 5 — Tests + gate (AC: #5)**.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/components/VulnerabilitiesTab.tsx:1-4` header comment — "a sortable, severity-filterable table
  of vulnerable packages. Fetches the report JSON (served inline by the backend); a failed phase shows the
  shared `TabFailureNotice`, and a clean scan shows an explicit zero-state rather than an empty table."
- Failure detection pattern (shared across tabs): the report request raises `ApiError` with
  `code === 'report_failed'` carrying `failureReason`; the tab renders `TabFailureNotice` with it.
- `frontend/src/api/reports.ts` — `getVulnerabilities(taskId)`; the analysis chord result shape is
  `{report_type, artifact_key, summary, failed, failure_reason}`.
- Epic 4 built the report: OSV findings plus NVD CWE enrichment (Story 4.2).
- Excel export is Story 8.13 — reimplemented server-side in **Story 21.17**, not here.

### Three distinct empty-ish states

There are three, and conflating any two of them is the likeliest defect: **clean scan** (report ran, found
nothing), **no data** (report absent), and **failed phase** (report errored, with a reason). The SPA
distinguishes all three; so must this.

### The shared failure notice starts here

`TabFailureNotice` is used by Stories 21.14, 21.15, and 21.16. Build it as a reusable partial in this story and
reuse it in the next two rather than copying it.

### Testing standards

- One test per empty-ish state, asserting the rendered text differs.
- A test asserting severity filtering is reflected in the querystring and survives a refresh.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.14: Vulnerabilities Tab]
- `frontend/src/components/{VulnerabilitiesTab,TabFailureNotice}.tsx`, `frontend/src/api/reports.ts`,
  `generate_sbom/analysis/services/vulnerability.py`.
- Upstream: `21-13-sbom-viewer-tab.md`. Downstream: `21-15`, `21-16` (reuse the failure partial), `21-17`.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **700 passed**, coverage **96.49%**; frontend **223 passed**.
- **20 new tests** in `tests/unit/test_vulnerabilities_tab.py`.
- Default sort verified by character position: the Critical package precedes the Low one, and
  `?sort=severity` reverses it.
- The three empty-ish states asserted **against each other**: rendering all three and putting
  them in a set must yield 3 distinct bodies.
- Severity filter: `?severity=Critical` drops the Low row; two identical requests are byte
  identical; `?severity=Bogus` shows **nothing** rather than everything.

### Completion Notes List

**A silent sorting bug, and the reason it was silent.** `Meta.order_by = "-severity_rank"`
looked right and did nothing: django-tables2 resolves `Meta.order_by` against **declared column
names**, and `severity_rank` is an accessor, not a column. The table simply rendered in
insertion order, which happened to look plausible. Corrected to `-severity` — the column, which
already carries `order_by="severity_rank"` — so it sorts by danger. The comment in `tables.py`
names the trap, because it produces no error and the wrong order is only visible if a test
checks which row comes first.

**Severity must never sort alphabetically**, and there is a test asserting the ranks directly
rather than only through the rendered page. Alphabetically "Critical" < "High" < "Low" <
"Medium", which would bury the worst findings under the least important ones — the exact
outcome this tab exists to prevent.

**Four states, not three, and they are asserted against each other.** The Dev Notes warn that
conflating any two of clean / missing / failed is the likeliest defect. I kept those three plus
the ordinary "has findings" case, and
`test_the_three_states_are_visibly_different` renders all three and asserts the set of bodies
has size 3 — a stronger check than three independent substring assertions, which would still
pass if two states rendered identically.

**A failed report is checked before its artifact.** A failed row also has no artifact, so
testing "no artifact" first would report a failure as merely *missing* and throw away the
reason. `read_report` orders the checks accordingly, and a test pins it.

**The shared failure notice is built here for 21.15 and 21.16.** `_failure_notice.html` and
`analysis/reports.read_report` are the reusable pieces those stories need — the Dev Notes were
explicit that this should be built once and reused rather than copied. `read_report` returns a
three-state `ReportResult` rather than a bare dict-or-None, so a caller cannot accidentally
treat "failed" as "missing".

**Filtering is a plain function, not a `FilterSet`.** django-filter operates on querysets, and
these rows come from a JSON artifact; forcing a queryset-shaped abstraction over a list would
have been more code and less clear. An unrecognised severity yields **no rows** rather than
silently falling back to all of them, so a stale link cannot present a filtered view as the
complete set.

**The filter form carries the active tab.** Without the hidden `tab` field, submitting the
severity filter would bounce the user back to Overview — a small thing that is only obvious
once the tab is inside a shell driven by `?tab=`.

**Rows are per finding, not per package,** matching the SPA's `toRows`: a package with three
findings becomes three rows. Identifier merging de-duplicates while preserving order (the SPA
used a `Set`), which a unit test covers directly since it is pure logic.

**One dispatch point for tab context.** `TAB_CONTEXT_BUILDERS` replaced the growing
`if tab == "sbom"` chain, and both the shell and the htmx partial go through `tab_context`, so
a tab rendered cold from `?tab=` and the same tab fetched by a click cannot diverge. 21.15 and
21.16 add one entry each.

**Not done here.** The Excel export of this report is Story 21.17. There is no pagination on
the findings table — the SPA had none, and adding it would exceed parity.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (5)**
- `src/django_apps/inventory/analysis/reports.py` — `ReportState`, `ReportResult`, `read_report`
  (**shared with 21.15/21.16**)
- `src/django_apps/inventory/analysis/tables.py` — `VulnerabilityTable`, `vulnerability_rows`,
  `SEVERITY_RANK`, `SEVERITY_BADGES`
- `src/django_apps/inventory/analysis/filters.py` — `filter_by_severity`
- `src/django_apps/inventory/templates/inventory/sbom/tabs/_failure_notice.html`
  (**shared with 21.15/21.16**)
- `tests/unit/test_vulnerabilities_tab.py` (20 tests)

**Modified (4)**
- `src/django_apps/inventory/sbom/pages.py` — `vulnerabilities_tab_context`,
  `TAB_CONTEXT_BUILDERS`, `tab_context`
- `src/django_apps/inventory/templates/inventory/sbom/tabs/_vulnerabilities.html` — the real tab
- `pyproject.toml` — mypy subclassing override extended to `inventory.analysis.tables`
- `tests/unit/test_results_page.py` — placeholder list narrowed again
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Filled in the Vulnerabilities tab: a django-tables2 table of findings with the SPA's columns, outbound advisory links, and Epic 4's CWE enrichment, sorted by severity **rank** descending so the worst findings lead, and filterable by severity through the querystring. The three empty-ish states — clean scan, no report, failed phase — are kept distinct and asserted against each other. Built the shared failure notice and the three-state `read_report` helper that Stories 21.15 and 21.16 reuse, and replaced the per-tab `if` chain with a single dispatch point. `pixi run ci` exit 0; 700 backend tests at 96.49%. |
