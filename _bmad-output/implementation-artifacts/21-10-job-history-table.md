---
baseline_commit: fbd103c
---

# Story 21.10: Job History Table

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.9**. Replaces `HistoryPage.tsx` (380 lines — the largest page in the
> SPA) **minus its live polling**, which Story 21.11 adds. This is the story that proves django-tables2 +
> django-filter can carry the four report tables that follow.

## Story

As a user,
I want a filterable, paginated table of my organisation's SBOM jobs,
so that I can find and act on past jobs without the SPA.

## Acceptance Criteria

1. **The table is converted.**
   Given `HistoryPage.tsx` renders columns Submitted, Manifest, Format, Output, Status, Elapsed, Results, when
   it is converted, then a django-tables2 table renders the same columns with the same status badges and
   elapsed-time formatting, ordered newest-first, and each row links to its results page.
2. **Pagination and filters match today's behaviour.**
   Given the SPA paginates at `PAGE_SIZE = 25` and filters by status (`All` / `In Progress` / `Completed` /
   `Failed`) and manifest format (`All` plus every canonical backend format code, `HistoryPage.tsx:49-53`),
   when filtering is converted, then a django-filter `FilterSet` provides both filters at page size 25, the
   format choices are derived from the backend's canonical list (Story 6.4 — the dropdown must not offer a
   value the backend rejects), and changing a filter resets to page 1 while remaining bookmarkable via
   querystring.
3. **Purged-artifact rows are indicated, not broken.**
   Given jobs whose artifacts were purged keep their metadata (Story 7.3), when such a job renders, then it
   shows the "Artifacts removed" indicator with its expiry date and its delete control is **disabled**.
4. **Per-job, bulk, and org-wide deletion work.**
   Given artifacts can be deleted per job, for a selection, or org-wide by an admin (FR-8.2, Story 7.2), when
   the actions are converted, then row checkboxes drive a "Delete selected" POST, the org-wide "Delete all
   artifacts" action is visible **and enforced** only for org admins, each is preceded by a confirmation
   naming exactly what will be removed, and in every case the **job records survive** while only the artifact
   files are deleted.
5. **The table is org-scoped.**
   Given **AD-2**, when a user views the page, then only their active org's jobs are listed, and a job from
   another org cannot be deleted by task id.
6. **Gate green.**
   When the story completes, then tests cover pagination, both filters, the empty state, the purged-artifact
   state, single/bulk/org delete, non-admin denial of the org-wide delete, and cross-org invisibility, and
   `pixi run ci` exits 0.

## Tasks / Subtasks

- [x] **Task 1 — `JobTable` (AC: #1)** — django-tables2; status badge and duration formatting as reusable
  column renderers.
- [x] **Task 2 — `JobFilterSet` (AC: #2)** — Status + manifest format; choices from the backend enum;
  querystring-driven.
- [x] **Task 3 — Purged-artifact rendering (AC: #3)** — Indicator + disabled delete.
- [x] **Task 4 — Delete actions (AC: #4, #5)** — Single, selected, org-wide; confirmation partial; admin gate
  on the org-wide action enforced in the view.
- [x] **Task 5 — Tests + gate (AC: #6)**.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/pages/HistoryPage.tsx:49-53` — `PAGE_SIZE = 25`;
  `STATUS_OPTIONS = ['All', 'In Progress', 'Completed', 'Failed']`;
  `FORMAT_OPTIONS = ['All', ...MANIFEST_FORMATS]` with the in-file comment: "never a hand-kept list, so the
  dropdown can't offer a value the backend rejects (Story 6.4, AC #4)".
- Columns rendered (`:331-338`): Submitted, Manifest, Format, Output, Status, Elapsed, Results, plus a
  checkbox column and a delete column.
- Expiry semantics (`:79-80`): `expired = status === 'SUCCESS' && !artifactsAvailable`; the tooltip shows
  `artifacts_expire_at`.
- Delete kinds (`:56`): `{ kind: 'single' } | { kind: 'selected' } | { kind: 'org' }`; the org-wide button is
  rendered only when `isAdmin` (`:293`).
- Confirmation copy (`:229-234`) is explicit that job records are kept and only SBOM/report files are removed —
  preserve that meaning.
- API: `listJobs({page, status, format})`, `deleteJobArtifacts(taskId)`, `bulkDeleteArtifacts({taskIds}|{all})`
  in `frontend/src/api/jobs.ts`.
- Pagination envelope (project convention): `PageNumberPagination`, `page_size=25`, max 100.

### Server-side sorting is a deliberate behaviour change

The SPA sorts some tables client-side on already-fetched data. Server-side ordering via querystring costs a
round trip per sort. That trade was accepted when the epic was scoped; do not reintroduce a client-side sorter
to hide it.

### Watch for

- **The admin gate on org-wide delete must be enforced in the view**, not merely by hiding the button — Story
  2.17 exists because that mistake was made before.
- **Selection across pages**: the SPA's "select all" selects only the current page (`toggleAll` uses
  `data.results`). Match that, and make the confirmation copy say so.
- **Deleting artifacts never deletes the job row** — assert it.

### Testing standards

- A test asserting that after an org-wide delete, the job count is unchanged and `result_key`/`artifact_key`
  are null.
- A test asserting a non-admin POST to the org-wide delete endpoint is refused.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.10: Job History Table]
- `frontend/src/pages/HistoryPage.tsx`, `frontend/src/api/{jobs,manifestFormats}.ts`,
  `frontend/src/components/JobStatusBadge.tsx`, `frontend/src/duration.ts`,
  `generate_sbom/sbom/{views,selectors,services}.py`.
- Upstream: `21-9-manifest-upload-and-job-submission-page.md`. Downstream: `21-11` (adds polling to these rows).
- Architecture: AD-2 (org scoping), AD-6 (storage triad — keys nulled on delete).

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **621 passed**, coverage **96.24%**; frontend **223 passed**.
- `mypy src` clean over 94 files; `ruff check .` clean.
- **31 new tests** in `tests/unit/test_history_page.py`.
- Routes: `ui-history` → `/history`, `ui-jobs-delete-artifacts` → `/history/artifacts/delete`,
  `ui-jobs-delete-all-artifacts` → `/history/artifacts/delete-all`.
- Pagination verified against the rendered table: 26 jobs → 25 rows on page 1, 1 on page 2.
- Duration formatting parametrised against `duration.ts`'s own cases: `None`/`-1` → `—`,
  `0.45` → `450ms`, `45` → `45s`, `83` → `1m 23s`, `7500` → `2h 05m`.
- Delete scopes: single, selection, and org-wide all leave `SBOMJob.objects.count()` unchanged
  with `result_key` nulled; a member gets **403** on the org-wide endpoint.

### Completion Notes List

**A real rendering bug, caught by the tests.** `render_status` originally read the column's
`value`, which raised `ValueError: 'Success' is not a valid SBOMJob.Status` on ten tests at
once. Because `status` is a field **with choices**, django-tables2 hands the renderer the
*display* label ("Success"), not the stored code ("SUCCESS") — and the badge map is keyed by
the code. It now reads `record.status`. Worth carrying into 21.13–21.16: any tables2 renderer
for a `choices` field will see labels, not codes.

**The status mapping is now shared rather than duplicated.** `selectors._STATUS_FILTERS`
became public `STATUS_FILTERS`, and `JobFilterSet.filter_status` imports it — the same mapping
the API filter uses. Two copies of "what does *In Progress* mean" is exactly the class of drift
Story 6.4 was about.

**Format choices come from `ManifestUpload.Format.choices`,** never a hand-kept list, carrying
over `HistoryPage.tsx`'s own comment. Two tests: the dropdown offers every canonical value, and
an unrecognised value yields an **empty page rather than an error** — which was Story 6.4's
actual symptom (a filter selection producing an error banner instead of rows).

**Both untyped libraries needed narrow mypy relief, not blanket ignores.** `django-filter` and
`django-tables2` ship no stubs, so their base classes are `Any` and strict mode's
`disallow_subclassing_any` rejects any subclass. Added `ignore_missing_imports` for the two
packages, plus `disallow_subclassing_any = false` scoped to exactly the three modules that must
subclass them (`sbom.filters`, `sbom.pages`, `sbom.tables`). Everything else in those files
stays fully checked.

**Deletion is one endpoint for single and selection, and a separate one for org-wide.** Single
and bulk are the same operation with a different number of ids, so sharing an endpoint avoids
duplicating the org scoping. The org-wide sweep gets its own URL specifically so it can carry
`OrgAdminRequiredMixin` rather than branching on role inside a view — and
`test_a_member_cannot_post_the_org_wide_delete` asserts the gate, not the hidden button
(Story 2.17's lesson).

**Cross-org safety is structural again.** Both delete views filter through `get_jobs(self.org)`,
so a task id from another org matches nothing — there is no branch that could treat it
differently. Three tests cover it: other-org rows invisible, other-org id undeletable, and the
org-wide sweep not reaching another org.

**Selection is per page, and the copy says so.** The SPA's `toggleAll` only ever covered fetched
rows; the header checkbox here does the same, and the confirmation text reads "the selected jobs
on this page" rather than implying it spans the filter. `test_the_confirmations_say_the_job_records_are_kept`
also pins the SPA's explicit promise that job records survive.

**Purged rows render, they do not break.** A completed job with no `result_key` shows the
"Artifacts removed" badge with its expiry date (Story 7.3), and deleting it again is reported as
a no-op rather than an error — `delete_job_artifacts` is already idempotent.

**Server-side sorting and paging, deliberately.** Filters, sort, and page all live in the
querystring, so any view is bookmarkable — the trade the epic accepted against the SPA's
client-side sort of already-fetched rows. Changing a filter starts at page 1 because the filter
form carries no `page` field, rather than stranding the user on a page that no longer exists.

**Not done here.** Live polling of in-progress rows is Story 21.11. The per-row "Results" link
still points at the SPA's `/results/{task_id}` until Story 21.12 converts it.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (4)**
- `src/django_apps/inventory/sbom/tables.py` — `JobTable`, `STATUS_BADGES`, `format_duration`
- `src/django_apps/inventory/sbom/filters.py` — `JobFilterSet`
- `src/django_apps/inventory/templates/inventory/sbom/history.html`
- `tests/unit/test_history_page.py` (31 tests)

**Modified (6)**
- `src/django_apps/inventory/sbom/pages.py` — `JobHistoryView`, `JobArtifactsDeleteView`,
  `JobArtifactsDeleteAllView`
- `src/django_apps/inventory/sbom/selectors.py` — `_STATUS_FILTERS` → public `STATUS_FILTERS`
- `src/django_apps/inventory/urls_pages.py` — three `ui-` routes
- `src/config/urls.py` — free `history` from the SPA catch-all
- `src/django_service/templates/_nav.html` — reverse `ui-history`
- `pyproject.toml` — mypy overrides for the two untyped table libraries
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Converted the job history to a django-tables2 table with a django-filter FilterSet: the same columns, status badges, and duration formatting as `HistoryPage.tsx`, paginated at 25, filterable by status and manifest format, all querystring-driven and bookmarkable. Status-filter semantics and format choices are imported from the backend's canonical definitions rather than restated (Story 6.4). Per-job, per-selection, and org-wide artifact deletion all keep every job record; the org-wide sweep is admin-gated in the view. `pixi run ci` exit 0; 621 backend tests at 96.24%. |
