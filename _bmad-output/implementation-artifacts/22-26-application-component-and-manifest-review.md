---
baseline_commit: c6c000b
---

# Story 22.26: Name the Application on Job Status, and Let the Manifest Be Read

Status: review

> **Product-owner direction:** *"I want to see the Application and Component information on the Job status
> page to the right of the Organization and the left of submitted. I also want to link back to the original
> manifest file on the Job status page too. We should be able to review the original manifest file."*

## Story

As someone scanning Job Status,
I want to see which application each job describes and to open the manifest it came from,
so that I can tell the rows apart and check a surprising result against its input.

**Context:** Two gaps, both about telling one job from another. The table showed the organization and the
manifest's *filename* — and the filename is often the same string on every row, so `requirements.txt`
identified nothing. Meanwhile the uploaded manifest was effectively **write-only**: parsed once and then
unreachable, so an SBOM that looked wrong could not be compared against what produced it.

## Acceptance Criteria

1. **Application and Component columns**, positioned between Organization and Submitted.
2. **The Manifest cell links to the uploaded file**, and the page shows its contents.
3. **The manifest page identifies its job** — application, component, organization, repository, branch.
4. **Content is escaped, never executed.** A manifest is whatever someone uploaded.
5. **A manifest too large to read, or missing from storage, says so** rather than breaking the page.
6. **Cross-org, like every other page** (Story 22.16).
7. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Write the failing tests first (AC: all)**
- [x] **Task 2 — Two columns on `JobTable`, in the requested position (AC: #1)**
- [x] **Task 3 — `render_manifest` links the cell (AC: #2)**
- [x] **Task 4 — `JobManifestView` + `manifest.html` (AC: #2, #3, #5, #6)**
- [x] **Task 5 — Verify the column order against the running app (AC: #1)**
- [x] **Task 6 — Gate (AC: #7)**

## Dev Notes

### Why a page and not a file download

A manifest is **user-uploaded content**. Serving it as a file response would let the upload influence how
the browser treats it; rendering it through `{{ }}` means Django escapes it and it can only ever be text.
That is also the better fit for the request — *review* the manifest, next to the job it produced, rather
than fetch it.

`MANIFEST_INLINE_MAX_BYTES` is 1 MB against an upload cap of 50 MB (FR-3.4). The limit is about what a
person can read on a page, not about what the server can send.

### Traps

- **Column order is the requirement, not a side effect.** The test asserts the header row's *positions*;
  a column appended at the end would satisfy "it shows the application" and still be wrong.
- **The row outlives the blob.** Purging clears artifacts and keeps metadata (FR-8.1), and local storage can
  simply lose a file — so a missing file is an expected state with its own message, not a 500.
- **`select_related("manifest", "org")` already covers the new columns**, so they cost no extra queries;
  a column reaching further would have introduced an N+1 on every row.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- 10 new tests in `tests/unit/test_manifest_review.py`; 9 failed before the implementation.
- Column order verified against the running app:
  `['Organization', 'Application', 'Component', 'Submitted', 'Manifest', …]`.
- `pixi run ci` — **exit 0**, 1092 tests, 97.27%.

### Completion Notes List

**The escaping test is the one that matters.** `<script>alert('xss')</script>` in a manifest renders as
text. It is the reason this is a page rather than a download, and without the assertion the decision would
read as a stylistic preference rather than the security choice it is.

**Two failure states rather than one.** "Too large to show" and "no longer available" are different facts
and a reader needs to know which — the first means the file is there and unreadable on a page, the second
that it is gone. Collapsing them into "unavailable" would have been less work and less useful.

### File List

**New (2)**
- `src/django_apps/inventory/templates/inventory/sbom/manifest.html`
- `tests/unit/test_manifest_review.py` (10 tests)

**Modified (3)**
- `src/django_apps/inventory/sbom/tables.py` — two columns, linked manifest cell
- `src/django_apps/inventory/sbom/pages.py` — `JobManifestView`, `MANIFEST_INLINE_MAX_BYTES`
- `src/django_apps/inventory/urls_pages.py` — `ui-job-manifest`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | Added Application and Component columns to Job Status between Organization and Submitted, and made the Manifest cell open the uploaded file. The manifest had been write-only since upload, so a surprising SBOM could not be checked against its input. Rendered into an escaped `<pre>` on a normal page rather than served as a file, because a manifest is whatever someone uploaded — a raw response would let it choose how the browser treats it. Too-large and missing files each get their own message. |
