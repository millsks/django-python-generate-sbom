---
baseline_commit: 396f44c
---

# Story 21.9: Manifest Upload and Job Submission Page

Status: review

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

- [x] **Task 1 — Upload form (AC: #1, #2)** — `FileField` + five fields; choices from the backend enum.
- [x] **Task 2 — View + service call (AC: #3, #4, #5)** — Call the existing submission service; map its
  rejections onto form errors; redirect on success.
- [x] **Task 3 — Concurrency-gate messaging (AC: #3)** — Surface the `Retry-After` guidance in human terms.
- [x] **Task 4 — Zero-org state (AC: #6)**.
- [x] **Task 5 — Tests + gate (AC: #7)**.

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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **590 passed**, coverage **96.21%**; frontend **223 passed**.
- `mypy src` clean over 92 files; `ruff check .` clean.
- **16 new tests** in `tests/unit/test_upload_page.py`; route `ui-upload` → `/upload`.
- **Refactor safety check:** after extracting `submit_job`, the full unit suite (**566 at that
  point**) passed with **one** change — the dispatch patch target in `tests/unit/test_jobs.py`.
  No API assertion changed.
- **Live server, real manifest:** logged in, GET `/upload` served the multipart form, POSTed a
  genuine `requirements.txt` with provenance →
  **302 → `/results/41838050-…`**; the job row read
  `status=PENDING`, `output_format=cyclonedx-json`, `application_id=APP-LIVE`.
- Rejection paths, each asserting **no** `SBOMJob` **and no** `ManifestUpload` row and
  `delay_on_commit` not called: unrecognised manifest, oversize file, concurrency limit,
  malformed URL, missing provenance fields, zero-org POST, CSRF-less POST.

### Completion Notes List

**The story's central instruction — "do not re-implement the concurrency gate, call the
existing path" — could not be followed literally, because there was no path to call.** The whole
submission sequence (gate → `upload_manifest` → `create_job` → `delay_on_commit`) lived **inline
in `GenerateJobView.post`**. Copying it into the page view is exactly what the instruction
forbids, so I extracted it instead:

- `sbom/services.py` gains `at_concurrency_limit(org)` — the single implementation of AD-7 —
  and `submit_job(...)`, which owns the gate, the AD-12 initial `PENDING` write, and the AD-10
  `delay_on_commit` dispatch.
- `GenerateJobView` now calls both. The page view calls `submit_job`. There is one
  implementation of the limit, so the API and the web UI cannot diverge on it.

**API parity was the risk in that refactor, and two details protect it.**
1. The gate is still checked in the DRF view **before** payload validation, exactly where it
   was. Moving it inside `submit_job` alone would have changed the response for a malformed
   payload from an at-limit org from **429** to **400**. `submit_job` re-checks the gate, which
   is a redundant count query and keeps the rule in one place.
2. The 429's `Retry-After` now reads `ConcurrencyLimitError.retry_after_seconds` rather than a
   literal `"60"`, so the header and the page's "try again in about a minute" wording cannot
   drift apart.

**One existing test had to change, and only one.** `tests/unit/test_jobs.py` patched
`inventory.sbom.views.run_sbom_pipeline.delay_on_commit`; dispatch no longer happens there. The
target moved to the task's own module, `inventory.tasks.sbom_pipeline.run_sbom_pipeline`, which
is arguably the better target anyway — it is the canonical object rather than a name re-exported
by whichever view dispatches. `submit_job` imports the task **lazily** because
`inventory.tasks.sbom_pipeline` imports `inventory.sbom.services`; a module-level import would
be circular. No assertion changed.

**AC #2 needed a labelled list that did not exist.** `OUTPUT_FORMAT_MAP` holds the canonical
values but no display labels — those lived only in the SPA's `OUTPUT_FORMATS`. Added
`OUTPUT_FORMAT_LABELS` and derived `OUTPUT_FORMAT_CHOICES` from the map beside it, so the form
cannot offer a value the backend rejects.
`test_output_format_choices_cover_every_supported_format` fails if a format is added to the map
without a label — which is precisely the drift that caused Story 6.4.

**A test of mine was silently not testing anything, and I caught it.** The oversize case set
`.size` on a `SimpleUploadedFile`, but the test client serialises the upload and Django rebuilds
the `UploadedFile` server-side — the faked size is discarded and the validator sees the real
(tiny) length. The test passed the file straight through to a **302**, which is how it surfaced.
It now patches the cap down instead, so the real page path is exercised; the reasoning is
written into the test so nobody restores the faked-size version.

**Rejections are field errors where a field is at fault, form errors where none is.**
Unsupported-format and parse failures attach to `file`; the concurrency limit attaches to the
form itself, because nothing the user typed is wrong — the message is the human form of the
API's `Retry-After` header. Every rejection re-displays the form with the user's input intact.

**Zero-org handling is inherited, not written.** `OrgMemberRequiredMixin` renders the shared
empty state in place of the page (Story 21.4), so this view contains no zero-org branch at all.
Tested both ways: the GET shows the empty state and no form, and a POST creates nothing.

**Submitting is a member capability.** `OrgMemberRequiredMixin`, not the admin mixin — matching
the API, where `GenerateJobView` requires only an active org. A plain (non-admin) member
submitting successfully is asserted.

**The redirect target is deliberately a literal path.** `/results/{task_id}` is still owned by
the SPA catch-all until Story 21.12 converts it, so `reverse("ui-job-results", …)` does not exist
yet. The comment names the story that will swap it — the same one-at-a-time handover the nav
uses.

**Not verified here:** that the pipeline actually *runs* to completion from a page submission.
The tests patch `delay_on_commit` (correctly — a unit test must not enqueue), and the live check
confirmed the job row and redirect but not the worker. Stories 21.11 and 21.12 exercise progress
and results, which is where that belongs.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (4)**
- `src/django_apps/inventory/sbom/forms.py` — `ManifestUploadForm`
- `src/django_apps/inventory/sbom/pages.py` — `UploadPageView`
- `src/django_apps/inventory/templates/inventory/sbom/upload.html`
- `tests/unit/test_upload_page.py` (16 tests)

**Modified (6)**
- `src/django_apps/inventory/sbom/services.py` — `at_concurrency_limit`, `submit_job`,
  `ConcurrencyLimitError`, `ACTIVE_STATUSES`, `OUTPUT_FORMAT_LABELS`, `OUTPUT_FORMAT_CHOICES`
- `src/django_apps/inventory/sbom/views.py` — `GenerateJobView` now calls the shared service
- `src/django_apps/inventory/urls_pages.py` — `ui-upload`
- `src/config/urls.py` — free `upload` from the SPA catch-all
- `src/django_service/templates/_nav.html` — reverse `ui-upload`
- `tests/unit/test_jobs.py` — dispatch patch target moved to the task's own module
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Converted manifest upload and job submission to a server-rendered page. The submission sequence — AD-7 concurrency gate, AD-12 initial PENDING write, AD-10 `delay_on_commit` dispatch — was extracted from the DRF view into `sbom.services.submit_job`, which both entry points now call, so the API and the web UI cannot diverge; the API's gate-before-validation ordering and its 429 payload are unchanged. Output-format choices are derived from the backend's canonical map (Story 6.4's lesson), success is POST-redirect-GET to the results URL, and every rejection re-displays the form with no job or upload row created. `pixi run ci` exit 0; 590 backend tests at 96.21%. |
