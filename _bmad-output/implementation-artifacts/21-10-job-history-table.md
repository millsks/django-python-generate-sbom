# Story 21.10: Job History Table

Status: ready-for-dev

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

- [ ] **Task 1 — `JobTable` (AC: #1)** — django-tables2; status badge and duration formatting as reusable
  column renderers.
- [ ] **Task 2 — `JobFilterSet` (AC: #2)** — Status + manifest format; choices from the backend enum;
  querystring-driven.
- [ ] **Task 3 — Purged-artifact rendering (AC: #3)** — Indicator + disabled delete.
- [ ] **Task 4 — Delete actions (AC: #4, #5)** — Single, selected, org-wide; confirmation partial; admin gate
  on the org-wide action enforced in the view.
- [ ] **Task 5 — Tests + gate (AC: #6)**.

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

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
