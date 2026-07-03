# Story 7.3: Expired-Artifact UI Indication

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want clear notice when a job's artifacts are gone,
so that I understand why downloads are unavailable while still seeing the job's summary.

## Acceptance Criteria

1. Given a job whose artifacts have been deleted (expired or manual), when I open its results page, then a notice states the artifacts are no longer available, including the expiry date, and download controls are disabled (FR-8.3).
2. Given an expired job on the results page, when it renders, then the retained job metadata (status, package count, summary statistics) remains visible (FR-8.3).
3. Given an expired job in the job history dashboard, when the list renders, then the row indicates artifacts are no longer available with the expiry date, while the job record stays in the list (FR-8.3).
4. Given the UI distinguishes an expired job from a failed job, when both appear, then each shows its own distinct indication (expired-artifacts notice vs. failure reason) (FR-8.3, FR-7.3).

## Tasks / Subtasks

- [ ] Task 1 — Surface expiry state in the API responses (AC: #1, #2, #3, #4)
  - [ ] Ensure the job status/detail serializer and the jobs-list serializer expose enough to derive "artifacts unavailable": `result_key is null` (post-cleanup) plus `artifacts_expire_at`, alongside `status`, `summary_stats`, `completed_at`
  - [ ] Define the derived flag (e.g. `artifacts_available = result_key is not None`) so the frontend does not infer from raw storage keys
- [ ] Task 2 — Results page expired notice (AC: #1, #2)
  - [ ] In `ResultsPage`, when `artifacts_available` is false, render an "Artifacts are no longer available" notice including the `artifacts_expire_at` date
  - [ ] Disable/hide the SBOM download button and per-tab download controls (e.g. Graph "Download SVG") when artifacts are gone
  - [ ] Keep retained metadata visible: Overview summary stats (total/vulnerable/license/version counts from `summary_stats`), status, timestamps (AC #2)
- [ ] Task 3 — History dashboard expired indicator (AC: #3)
  - [ ] In `HistoryPage`, mark rows with unavailable artifacts using a distinct indicator + the expiry date; keep the row in the list (record is retained)
  - [ ] Results link may still open the page (which shows the expired notice) — do not remove the row
- [ ] Task 4 — Distinguish expired vs failed (AC: #4)
  - [ ] Ensure the expired-artifacts indication is visually and semantically distinct from a `FAILED` job's failure-reason indication (from Story 6.1 / FR-7.3)
  - [ ] A job can be `SUCCESS` + expired (artifacts gone) — this must read differently from `FAILED`
- [ ] Task 5 — Tests (AC: #1–#4)
  - [ ] Frontend: results page renders the expired notice + retained stats + disabled downloads when `artifacts_available=false`
  - [ ] Frontend: history row shows the expired indicator with expiry date and remains listed
  - [ ] Frontend: expired (`SUCCESS`, no artifacts) vs `FAILED` render distinct indications
  - [ ] Backend: serializer exposes `artifacts_available` / `artifacts_expire_at` correctly for cleaned vs live jobs

## Dev Notes

### What "expired" means in data terms

After cleanup (Story 7.1 scheduled or 7.2 manual), a job has `result_key = null` and its `AnalysisReport.artifact_key`s nulled, but the `SBOMJob` row and `summary_stats` persist (FR-8.1). The UI keys off `result_key is null` (surfaced as `artifacts_available=false`) together with `artifacts_expire_at` for the date shown. `summary_stats` (`total_packages`, `vulnerability_count`, license/version breakdowns) remains the source for the retained Overview metrics. [Source: solution-design.md § 3.3; § 4.5]

### Expired vs failed are different states (AC #4)

- Expired: `status == SUCCESS` (job succeeded) but artifacts were cleaned → "no longer available" notice + expiry date, metadata intact.
- Failed: `status == FAILED` with a `failure_reason` → failure notice (Story 6.1 / FR-7.3), no successful artifacts ever existed.

Render these with distinct affordances so a user is never confused about which happened.

### Frontend conventions (AD-5)

- All data fetched via `frontend/src/api/` (`jobs.ts`); no direct fetch in components.
- This is presentation over existing endpoints — it does not add new business logic to the backend beyond exposing the derived availability flag.

### Dependency / sequencing notes

- Depends on the cleanup states produced by Stories 7.1/7.2 (nulled `result_key`).
- Depends on `ResultsPage` (Epic 5) and `HistoryPage` (Epic 6) existing — this story augments both with the expired state. Schedule after Epics 5 and 6.
- Depends on the failed-job indication from Story 6.1 to contrast against (AC #4).

### Project Structure Notes

- Changes are frontend-heavy (`ResultsPage`, `HistoryPage`, shared status/notice components) plus a small serializer field on the backend jobs/status responses.
- No new models or migrations.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.3: Expired-Artifact UI Indication]
- [Source: solution-design.md#3.3 sbom/ — SBOMJob model (result_key, summary_stats, artifacts_expire_at)]
- [Source: solution-design.md#4.5 Celery Beat — artifact cleanup]
- [Source: solution-design.md#7. Frontend Architecture]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA: REST API only]
- [Source: prd.md#FR-8.3, FR-7.3]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
