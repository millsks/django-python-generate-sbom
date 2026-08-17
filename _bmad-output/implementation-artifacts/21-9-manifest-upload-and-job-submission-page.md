# Story 21.9: Manifest Upload and Job Submission Page

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.8**. The primary user journey — the first story that exercises the
> pipeline from a server-rendered page.

## Story

As a user,
I want to upload a manifest and start an SBOM job from a server-rendered form,
so that I can generate SBOMs without the SPA.

## Acceptance Criteria

1. **The upload form is converted.**
   Given `UploadPage.tsx` posts a file plus Application ID, Component name, Repository URL, Source branch
   (default `main`), and Output format, when it is converted, then a Django `Form` with a `FileField` and the
   same five fields — rendered `enctype="multipart/form-data"` through crispy — replaces it, with all five
   preserved as required exactly as they are today.
2. **Choice lists come from the backend, never a hand-kept copy.**
   Given Story 6.4 fixed a bug caused by the frontend and backend format lists drifting apart, when the form is
   built, then the output-format choices are sourced from the backend's canonical list (as
   `OUTPUT_FORMATS`/`DEFAULT_OUTPUT_FORMAT` are today), so the form cannot offer a value the backend rejects.
3. **Rejections render as form errors.**
   Given the upload path enforces file-type and size validation (NFR-3.4) and a per-org concurrency gate
   (**AD-7**: returns `429` with `Retry-After` when at `SBOM_MAX_CONCURRENT_JOBS_PER_ORG`), when a submission
   is rejected, then the reason renders as an error on the re-displayed form — the concurrency rejection
   specifically telling the user to retry later — and **no job is created**.
4. **Success is POST-redirect-GET.**
   Given a successful submission currently navigates to `/results/{task_id}`, when the form succeeds, then the
   view **redirects** to the results URL for the new task so a browser refresh cannot double-submit.
5. **Dispatch invariants are preserved.**
   Given **AD-10** requires `delay_on_commit()` for task dispatch from within a transaction and **AD-12**
   makes the view the sole exception permitted to set the initial status, when a job is submitted, then
   dispatch still goes through `delay_on_commit()` and the view still sets `status='PENDING'` before dispatch —
   these invariants are **not** re-implemented, the existing service is called.
6. **Zero-org users cannot submit.**
   Given a user with no active org cannot submit, when they reach the page, then they see the zero-org state
   from Story 21.4 instead of the form.
7. **Gate green.**
   When the story completes, then tests cover a valid upload end to end, each rejection path (bad type,
   oversize, concurrency limit), the redirect, and the zero-org state, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — Upload form (AC: #1, #2)** — `FileField` + five fields; choices from the backend enum.
- [ ] **Task 2 — View + service call (AC: #3, #4, #5)** — Call the existing submission service; map its
  rejections onto form errors; redirect on success.
- [ ] **Task 3 — Concurrency-gate messaging (AC: #3)** — Surface the `Retry-After` guidance in human terms.
- [ ] **Task 4 — Zero-org state (AC: #6)**.
- [ ] **Task 5 — Tests + gate (AC: #7)**.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/pages/UploadPage.tsx` — fields: file, `applicationId`, `componentName`, `repositoryUrl`
  (`type="url"`), `sourceBranch` (default `'main'`), `outputFormat` (default `DEFAULT_OUTPUT_FORMAT`); all five
  text fields are `required`; on success it navigates to `/results/${response.task_id}`.
- `frontend/src/api/jobs.ts` — `OUTPUT_FORMATS`, `DEFAULT_OUTPUT_FORMAT`, `generateSbom(file, {...})`.
- **AD-7** — concurrency gate in `manifests/views.py` **before** enqueue: counts `PENDING`/`PROGRESS` jobs for
  the org, returns `429` + `Retry-After` at or above `settings.SBOM_MAX_CONCURRENT_JOBS_PER_ORG`.
- **AD-10** — always `task.delay_on_commit()`; **AD-12** — `SBOMJob.status` is written only by Celery task
  code, with `manifests/views.py` setting the initial `PENDING` as the sole exception.
- Storage path convention: `manifest-uploads/{org_id}/{upload_id}/{filename}`.
- Story 6.4 is the cautionary precedent for hand-kept choice lists (the manifest-format filter bug).

### Django's file handling replaces manual multipart assembly

`generateSbom` builds a `FormData` by hand today. A Django `FileField` on a `multipart/form-data` form gives
the same result with server-side size and type validation available declaratively.

### Watch for

- **Do not re-implement the concurrency gate** in the view — call the existing path so the API and the web UI
  cannot diverge on the limit.
- **`repositoryUrl` is `type="url"` today** — use `URLField` so the validation is at least as strict.
- **Large uploads**: confirm `DATA_UPLOAD_MAX_MEMORY_SIZE`/`FILE_UPLOAD_MAX_MEMORY_SIZE` are adequate for real
  lockfiles, and that exceeding them produces a form error rather than a 500.

### Testing standards

- An end-to-end test that submits a real fixture manifest and asserts a job row is created with
  `status='PENDING'` and that dispatch was deferred to commit.
- A test asserting no job row is created on each rejection path.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.9: Manifest Upload and Job Submission Page]
- `frontend/src/pages/UploadPage.tsx`, `frontend/src/api/jobs.ts`,
  `generate_sbom/manifests/{views,services,detection}.py`.
- Upstream: `21-8-global-administration-page.md`. Downstream: `21-10`, `21-11`, `21-12`.
- Architecture: AD-7 (concurrency gate), AD-10 (`delay_on_commit`), AD-12 (status ownership), AD-3.

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
