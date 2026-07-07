# Story 16.3: Consolidated De-Duplicated SBOM by Application ID

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Fourth story of Epic 16 — build after 8.26.** It reads the **stored** SBOM documents of the completed
> jobs for one Application ID and merges them, deduping by **(name, version, ecosystem)** — a key that only
> works once ecosystem is written into the document. **Hard dependency: Story 8.26 (ecosystem in the SBOM
> document).** Also needs 16.1 (`ManagerRoute` / `has_management_access`) and 16.2 (the rollup surface the
> action hangs off). Build order: 16.1 → 16.2 → **8.26** → **16.3** → 16.4.

## Story

As a manager (or admin/global-admin),
I want to download one consolidated, de-duplicated SBOM for an Application ID,
so that I get a single standards-compliant document covering all of that application's completed results
without duplicate components across its manifests/jobs.

## Acceptance Criteria

1. **Merge scope — one Application ID (manager tier).**
   Given a manager (or admin/global-admin) and an Application ID with ≥1 completed job in the active org,
   when they request a consolidated SBOM, then the engine unions the components of **all completed results
   for that single Application ID** and emits **one** document. A manager may consolidate only **within a
   single Application ID** — no cross-App-ID selection (that is admin-only, Story 16.4).
2. **De-dup identity = (name, version, ecosystem).**
   Given components merged across results, when deduplicated, then two components are the same iff their
   **name, version, AND ecosystem** all match. **PyPI and conda are kept distinct** — `numpy 1.26.0` (pypi)
   and `numpy 1.26.0` (conda) are two components, not one. (This is exactly why Story 8.26 must embed
   ecosystem in the stored document — the dedupe reads ecosystem back out of it.)
3. **Reads the STORED documents.**
   Given the completed results, when merging, then the engine reads each job's **persisted SBOM document**
   (the blob at `result_key`, parsed via `sbom/document.py::normalize_components`) and unions those component
   sets — it does **not** re-resolve manifests or regenerate per-job SBOMs.
4. **Only completed results included.**
   Given an Application ID with a mix of completed, pending, and failed jobs, when consolidating, then only
   **completed** results contribute components; pending/failed are skipped (and, where useful, reported as
   skipped) so the merge never blocks on or mis-includes an unfinished job.
5. **One standards SBOM out, with merged provenance.**
   Given the merged component set, when the document is built, then it is a valid standards SBOM —
   **CycloneDX** (primary; note **SPDX** too where the generator supports it) — with `application:id` set to
   the Application ID and metadata marking it an **aggregate/merged** document (distinct from a single-job
   SBOM), referencing the source jobs in provenance. Each component carries its ecosystem (from
   8.26) so the merged document is itself round-trippable.
6. **Deterministic output.**
   Given the same set of completed results, when consolidated twice, then the output is **deterministic** —
   components in a stable sort order (e.g. by ecosystem, name, version), so byte-diffs are meaningful and
   tests are stable.
7. **Manager-accessible, gated + downloadable.**
   Given the management surface (Story 16.2), when a manager triggers "consolidate" for an Application ID,
   then the endpoint is gated by `has_management_access` (Story 16.1, 403 otherwise) and returns the merged
   SBOM as a download (same delivery pattern as the existing single-job SBOM download). Wrapped in
   `ManagerRoute` on the frontend.
8. **Tested; CI green.**
   Backend + frontend tests per the Tasks; `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Merge/dedupe engine (AC: #1, #2, #3, #4, #6)**
  - [ ] A pure, independently-testable merge function: input = the parsed component lists of N stored
    documents (via `sbom/document.py::normalize_components`), output = one deduped, sorted component list.
    Dedupe key = `(name, version, ecosystem)` — build a dict/set keyed on that tuple; **pypi≠conda** (AC #2).
    Sort deterministically (AC #6). Keep it I/O-free (the task fetches the blobs and passes parsed components
    in) so it is unit-testable with fixtures, mirroring the `generation.py` purity contract (Story 3.4).
  - [ ] Emit the merged CycloneDX (and SPDX where supported) document from the deduped set, reusing the
    existing `sbom/generation.py` serializer paths where practical; set `application:id` = the App ID and mark
    the metadata as an aggregate/merged doc referencing the source jobs (AC #5). Each component keeps its
    ecosystem (8.26 property + purl type).
- [ ] **Task 2 — Endpoint (AC: #1, #4, #7)**
  - [ ] `GET /api/v1/management/application-rollup/<application_id>/consolidated-sbom/` (or similar), gated by
    `has_management_access` (Story 16.1). It gathers the **completed** jobs for that Application ID in the
    **active org** (org isolation, AD-2; skip pending/failed, AC #4), loads each stored document from
    `result_key`, runs the merge engine, and returns the document as a download (reuse the single-job SBOM
    download delivery — content-type + filename headers). A manager may only target a single App ID (AC #1).
- [ ] **Task 3 — Frontend action (AC: #7)**
  - [ ] On the 16.2 rollup page, add a per-Application-ID "Download consolidated SBOM" action (manager-visible)
    calling the new endpoint; `frontend/src/api/management.ts` gains the client. Wrapped in `ManagerRoute`.
- [ ] **Task 4 — Tests (AC: #8)**
  - [ ] Backend unit (engine): merging two documents dedupes identical `(name, version, ecosystem)` to one;
    **keeps a pypi and a conda component of the same name/version as two** (the load-bearing case); output is
    deterministically sorted; an empty/partial input degrades cleanly.
  - [ ] Backend integration/endpoint: only completed jobs for the target App ID (in the active org) contribute;
    pending/failed skipped; org isolation (a second org's jobs never merged); 403 for a plain member; the
    response is a valid downloadable SBOM with `application:id` = the App ID and aggregate metadata.
  - [ ] Frontend: the consolidate action calls the endpoint and triggers a download; `ManagerRoute` gates it.
  - [ ] `pixi run ci` green.

## Dev Notes

### The dependency on 8.26 (do not start before it)

The dedupe identity is **(name, version, ecosystem)**, and ecosystem is only reliably available if it lives in
the **stored** SBOM document. Story 8.26 embeds `PackageSpec.ecosystem` into the document (a `package:ecosystem`
property + a correct purl type) and parses it back in `document.py`. Until 8.26 lands, `normalize_components`
does not return ecosystem, and the pypi-vs-conda distinction (AC #2) cannot be made. **8.26 is a hard
prerequisite.** (If ecosystem is somehow needed before 8.26 merges, STOP — do not fake it from name heuristics;
that would violate the product decision that pypi/conda stay distinct.)

### Read stored documents — this is the one place that reads blobs

Unlike 16.2 (which reads DB summaries only), 16.3 must read the **persisted SBOM documents** of the completed
jobs and union their component lists via `sbom/document.py::normalize_components` (the same parse-back the SBOM
viewer uses, `document.py:18,203-215`). It does **not** re-resolve manifests or regenerate per-job SBOMs — the
inputs are the already-generated, stored documents (AD-6: keys/blobs already persisted). Gather the blobs in
the task/endpoint; keep the merge function itself pure.

### Manager vs admin merge tiering (product decision)

- **Manager (this story):** may consolidate only **within one Application ID** — the merge set is exactly the
  completed jobs sharing that App ID. No arbitrary selection.
- **Admin (Story 16.4):** may arbitrarily multi-select any results across App IDs and merge them. 16.4 reuses
  **this** engine and dedupe key; it only adds the selection UI + the stricter admin gate.

Build the engine here as a reusable pure function so 16.4 is purely selection + gating on top of it.

### Determinism + provenance

Sort the merged components by a stable key (ecosystem, name, version) so repeated runs are byte-identical
(AC #6) — important for downstream diffing and for stable tests. Mark the document as an **aggregate/merged**
SBOM (metadata) distinct from a single-job SBOM, set `application:id` to the App ID, and reference the source
jobs in provenance so a consumer can trace what was merged.

### Project Structure Notes

- Backend: a merge engine module (pure) + a management endpoint that loads completed-job blobs and returns the
  download; reuse `sbom/document.py` (parse-back) and `sbom/generation.py` (serialize) paths; gate with
  `has_management_access` (16.1); org-scope with AD-2.
- Frontend: extend `api/management.ts` + the 16.2 rollup page with the consolidate action, under `ManagerRoute`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.3: Consolidated SBOM by Application ID]
- **Prerequisite:** `8-26-ecosystem-field-in-sbom-document.md` (ecosystem in the stored document — the dedupe key)
- Stored-document parse-back: `backend/generate_sbom/sbom/document.py:18,203-215`; serialize: `sbom/generation.py`
- Grouping key: `backend/generate_sbom/manifests/models.py:47` (`application_id`), `sbom/generation.py:106`
  (`application:id` property), `document.py:67` (read back)
- Gate + guard: `has_management_access`, `ManagerRoute`, `is_manager` (Story 16.1); rollup surface (Story 16.2)
- Single-job SBOM download delivery (reuse the pattern): existing SBOM Results download
- AD-6 (keys/blobs persisted; read, don't rewrite): memory `phase3-writes-blob-not-phase8`
- Related: `16-1-...md`, `16-2-...md`, `16-4-admin-multi-select-consolidated-sbom.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
