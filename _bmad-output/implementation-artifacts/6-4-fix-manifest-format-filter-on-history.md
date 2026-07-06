# Story 6.4: Fix the Manifest-Format Filter on the History Page (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to filter my SBOM jobs by any manifest format the History page offers,
so that selecting a real format (e.g. `pixi_toml`) shows the matching jobs instead of an error banner.

## Acceptance Criteria

1. Given the History page ("Your SBOM jobs") with the **Manifest format** filter, when I select any format the dropdown offers — explicitly `pixi_toml`, and each of the other current formats (`requirements`, `pyproject`, `pixi_lock`, `conda`) — then `GET /api/v1/sbom/jobs/?format=<value>` returns `200` with only the jobs whose manifest matches that format, and the table renders those rows; the "Could not load your jobs." error banner never appears.
2. Given the **Manifest format** filter set to **All**, when the jobs list is served, then the behavior is unchanged — all of the org's jobs are returned regardless of manifest format (no regression).
3. Given the backend jobs-list filter, when it receives an unknown or invalid `format` value, then it degrades gracefully — an empty result set (or the value is ignored) — and never returns a `400`/`500`, so a stale UI can never turn a filter selection into the error banner.
4. Given the frontend format options and the backend accepted formats, when the manifest-format list changes (e.g. Epic 8's pixi/conda work adds or renames a format), then both derive from one canonical source (the backend `ManifestUpload.Format` codes), so the UI can never offer a value the backend rejects; a test asserts the two stay consistent so drift fails CI.
5. Given the change, when complete, then it is covered by tests: a backend test asserting `GET /api/v1/sbom/jobs/?format=pixi_toml` returns the matching job(s) with `200` (and an invalid value degrades cleanly, not a `500`), and a frontend test asserting that selecting a format issues the request with the right `format` param and renders results rather than the error state; `pixi run ci` is green (backend coverage ≥90%).

## Root-Cause Analysis

**Symptom (two screenshots).** On the History page, a job row shows Format = `pixi_toml`. With the **Manifest format** filter on **All** the row renders fine; selecting **`pixi_toml`** replaces the table with the banner **"Something went wrong — Could not load your jobs."** So filtering by a real manifest format makes the jobs-list request fail, and the frontend's catch-all error fallback fires.

**Where the banner comes from.** `apiRequest` throws an `ApiError` on any non-2xx response (`frontend/src/api/client.ts:75-76`, via `toApiError`). `HistoryPage` catches the rejected `listJobs()` promise and sets `error` (`frontend/src/pages/HistoryPage.tsx:166`, effect at ~`:176-189`), which renders `<ErrorState message="Could not load your jobs." />` (`frontend/src/pages/HistoryPage.tsx:304-305`). This banner is the generic fallback for *any* failed jobs-list request — it masks the real 4xx/5xx cause. So the defect is: the filtered request returns a non-2xx.

**Two independent, hand-maintained format lists (the drift root cause).**
- Backend canonical enum: `ManifestUpload.Format` — `requirements`, `pyproject`, `pixi_lock`, `pixi_toml`, `conda` (`backend/generate_sbom/manifests/models.py:25-30`), stored on `detected_format` (`manifests/models.py:43`).
- Frontend dropdown: `FORMAT_OPTIONS = ['All', 'requirements', 'pyproject', 'pixi_lock', 'pixi_toml', 'conda']` hardcoded in `frontend/src/pages/HistoryPage.tsx:50`, sent verbatim as the `format` query param (`HistoryPage.tsx:181` → `listJobs({ format })` → `frontend/src/api/jobs.ts:100-107`, `params.set('format', query.format)`).

These two lists are maintained by hand with no shared source of truth. Epic 8 (Stories 8.18/8.19) reworks conda/pixi manifest handling; any rename or addition of a `Format` code on the backend that the frontend list does not mirror (or vice versa) makes the UI offer a value the backend can't match — the exact drift this bug demonstrates.

**Why the request fails on the offered value.** The list flows through `JobsListView.get_queryset` (`backend/generate_sbom/sbom/views.py:123-138`), which reads `format` from `request.query_params` and passes it to `selectors.get_jobs(org, ..., format_filter=...)`. The selector applies `jobs.filter(manifest__detected_format=format_filter)` (`backend/generate_sbom/sbom/selectors.py:34-48`).

At the current worktree commit that raw `.filter(...)` returns an *empty* queryset for an unrecognized value (no `500`), and the frontend/backend literals happen to match — so the defect reproduces only once drift is introduced OR once a validation layer is added:
- **Drift path:** after Epic 8 renames/adds a format on one side only, the UI sends a code the backend enum no longer recognizes → empty (best case) or, combined with the next path, a hard error.
- **Validation path:** Story 11.19 formalizes the `format` query param and its allowed values in the OpenAPI schema. If that param is enforced as a `ChoiceField` / `OpenApiParameter(enum=...)` built from a **stale** allowed-set (one that predates `pixi_toml`/the Epic 8 formats), a legitimately-offered value is rejected with a `400` → the reported banner. This story must ensure any such enforced enum is sourced from the same canonical `ManifestUpload.Format` codes.

**Conclusion.** The fix has two parts: (1) make the backend `format` filter accept every canonical `Format` code and degrade gracefully (empty/ignore, never 4xx/5xx) on anything else; (2) source the frontend `FORMAT_OPTIONS` from the backend's canonical format codes (and add a test asserting the frontend options are a subset of the backend enum) so the two lists can never drift into an offer-a-rejected-value state again.

## Tasks / Subtasks

- [ ] Task 1 — Backend: filter accepts all canonical formats, degrades gracefully (AC: #1, #2, #3)
  - [ ] Confirm `selectors.get_jobs` (`backend/generate_sbom/sbom/selectors.py:34-48`) filters `manifest__detected_format` against every `ManifestUpload.Format` value, including `pixi_toml`
  - [ ] Ensure an unknown/invalid `format` value yields an empty queryset (or is ignored) — never raises; verify `JobsListView.get_queryset` (`backend/generate_sbom/sbom/views.py:129-138`) has no path that turns a bad `format` into a `400`/`500`
  - [ ] If Story 11.19's schema work introduced (or will introduce) a `ChoiceField`/`OpenApiParameter(enum=...)` for `format` on this endpoint, source its choices from `ManifestUpload.Format.values` (single source of truth) — not a hand-listed set
  - [ ] Keep **All** = no `format` param = no format filter (unchanged behavior)
- [ ] Task 2 — One canonical format source shared with the frontend (AC: #4)
  - [ ] Expose the canonical `ManifestUpload.Format` codes to the frontend in a single, testable way (options: the OpenAPI schema from 11.19, a small read-only endpoint, or a generated/asserted constant) — pick the lightest approach consistent with the current merged state
  - [ ] Replace the hardcoded `FORMAT_OPTIONS` in `frontend/src/pages/HistoryPage.tsx:50` so its non-`All` entries derive from that canonical source
- [ ] Task 3 — Tests (AC: #5)
  - [ ] Backend: `GET /api/v1/sbom/jobs/?format=pixi_toml` returns the matching job(s) with `200`; each canonical `Format` value returns `200` and filters correctly; an invalid value returns `200` with an empty (or unfiltered-per-decision) result, never `500`
  - [ ] Frontend: selecting a manifest format issues `listJobs` with the correct `format` param and renders result rows (not the `ErrorState`); a consistency test asserts the frontend format options are a subset of the backend canonical codes so drift fails CI
  - [ ] Confirm `pixi run ci` exits 0 with backend coverage ≥90%

## Dev Notes

### Endpoint & filter contract

`GET /api/v1/sbom/jobs/` reads `status` and `format` from `request.query_params` (`backend/generate_sbom/sbom/views.py:135-137`) and delegates to `selectors.get_jobs` (`backend/generate_sbom/sbom/selectors.py:34-48`). The `format` filter targets `manifest__detected_format`. `All` (or absent) means no format filter — the frontend already drops `status=All`/absent `format` in `listJobs` (`frontend/src/api/jobs.ts:100-107`). [Source: 6-1-jobs-list-api-and-dashboard-table.md; solution-design.md#5.2]

### Canonical manifest formats (single source of truth)

`ManifestUpload.Format` (`backend/generate_sbom/manifests/models.py:25-30`) is the one true list: `requirements`, `pyproject`, `pixi_lock`, `pixi_toml`, `conda`. Detection maps filenames to these codes (`backend/generate_sbom/manifests/detection.py:27-31`) and parsers key off them (`backend/generate_sbom/sbom/parsers/__init__.py:29`). Both the jobs-list `format` filter and the History dropdown must derive from this enum. [Source: ARCHITECTURE-SPINE.md#AD-2/AD-5; Epic 8 Stories 8.18/8.19]

### Frontend error fallback

`apiRequest` rejects with `ApiError` on non-2xx (`frontend/src/api/client.ts:75-76`); `HistoryPage` maps any such rejection to the single "Could not load your jobs." banner (`HistoryPage.tsx:166`, `:304-305`). The banner is intentionally generic, so the fix must remove the *cause* (a non-2xx on a legitimately-offered format), not special-case the banner. [Source: solution-design.md#7.2]

### Coordination / sequencing

- **Story 11.19** (OpenAPI/Swagger schema completeness, merged on `main`) documents the `format` query param and its allowed values. If the format-enum is enforced there, it must be built from `ManifestUpload.Format.values`. Implement 6.4 against the then-current merged state so the enforced enum and the filter agree.
- **Epic 8 Stories 8.18/8.19** rework conda/pixi manifest resolution and are the likely trigger for future format drift. The canonical-source AC (#4) is what prevents a repeat.
- No change to status filtering, pagination, live polling (6.2), or the elapsed column (6.3).

### Project Structure Notes

- Backend: `backend/generate_sbom/sbom/selectors.py` (`get_jobs`), `backend/generate_sbom/sbom/views.py` (`JobsListView`), `backend/generate_sbom/manifests/models.py` (`ManifestUpload.Format` — canonical enum). Tests in `backend/tests/unit/test_jobs_list.py`.
- Frontend: `frontend/src/pages/HistoryPage.tsx` (`FORMAT_OPTIONS`), `frontend/src/api/jobs.ts` (`listJobs`). Tests in `frontend/src/pages/HistoryPage.test.tsx`.
- Selectors stay read-only; keep filtering logic in `get_jobs`, not the view (file-roles convention).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.4: Fix the Manifest-Format Filter on the History Page (Bugfix)]
- [Source: _bmad-output/implementation-artifacts/6-1-jobs-list-api-and-dashboard-table.md]
- [Source: backend/generate_sbom/sbom/selectors.py:34-48 — get_jobs format filter]
- [Source: backend/generate_sbom/sbom/views.py:123-138 — JobsListView.get_queryset]
- [Source: backend/generate_sbom/manifests/models.py:25-30 — ManifestUpload.Format (canonical)]
- [Source: frontend/src/pages/HistoryPage.tsx:50, :181, :304-305 — FORMAT_OPTIONS, filter, error banner]
- [Source: frontend/src/api/jobs.ts:94-107 — listJobs / format param]
- [Source: frontend/src/api/client.ts:75-76 — non-2xx → ApiError]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA: REST API only]

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
