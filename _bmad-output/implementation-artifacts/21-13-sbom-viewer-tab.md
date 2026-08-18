---
baseline_commit: b703938
---

# Story 21.13: SBOM Viewer Tab

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.12**. Fills the second tab of the shell that story built.

## Story

As a user,
I want to read the generated SBOM in the browser,
so that I do not have to download it to inspect it.

## Acceptance Criteria

1. **Both views are converted.**
   Given `SbomTab.tsx` offers a structured **component table** and a **raw document** view behind a toggle
   (Story 8.6), when it is converted, then both views are available behind the same toggle, defaulting to the
   component table, reading the document through the existing inline-document selector.
2. **The component table keeps its columns and enrichment.**
   Given the table shows package name, version, licence (Story 8.25), ecosystem (Stories 8.8/8.26), and
   direct/transitive information (Stories 8.3–8.5), when it is converted, then all of those still render, and
   the metadata block from Story 8.11 is preserved.
3. **Sorting moves to the server.**
   Given the SPA sorts the component table client-side, when it is converted, then sorting is server-side via
   querystring on the same columns, with the same default sort (Story 8.16).
4. **A large raw document does not block the page.**
   Given a raw SBOM document can be several megabytes, when the raw view renders, then it is served without
   blocking the rest of the page and without loading the entire document into the tab's initial payload.
5. **Unavailable artifacts show a notice, not an error.**
   Given an expired or purged artifact (Story 7.3), when the document is missing, then the tab shows the
   retention notice — the SPA's own comment is explicit that "an unavailable/expired artifact shows a notice,
   not an error".
6. **Gate green.**
   When the story completes, then tests cover both views, sorting, the default sort, and the unavailable
   state, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [x] **Task 1 — Component table (AC: #1, #2, #3)** — django-tables2; server-side ordering; all enrichment
  columns.
- [x] **Task 2 — Raw view (AC: #1, #4)** — Separate htmx-loaded partial or a streamed response; not part of
  the tab's initial payload.
- [x] **Task 3 — Toggle (AC: #1)** — Segmented control; component table is the default.
- [x] **Task 4 — Unavailable state (AC: #5)**.
- [x] **Task 5 — Tests + gate (AC: #6)**.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/components/SbomTab.tsx:1-4` header comment — "Two views — a structured component table and the
  raw document text — toggled by a segmented control. Content comes from the inline document endpoint (AD-5);
  an unavailable/expired artifact shows a notice, not an error."
- `type View = 'components' | 'raw'`, defaulting to `'components'`; sort state is `'asc' | 'desc'`.
- `frontend/src/api/sbom.ts` — `getSbomDocument(taskId)` → `SbomDocument` with `SbomComponent[]`.
- Enrichment already embedded in the document: licence (Story 8.25), ecosystem + purl type (Story 8.26),
  direct/transitive (Stories 8.3–8.4), metadata block (Story 8.11).
- Excel export of components is Story 8.27 — reimplemented server-side in **Story 21.17**, not here.

### The raw view is the size risk

The SPA fetches the whole document as JSON and renders it. Server-side, embedding a multi-megabyte document in
the tab's HTML would make the results page unusable for large projects. Load it in its own request, and
consider a streamed response or a size cap with a "download instead" affordance.

### Watch for

- **`AD-11`** — downloads redirect to a presigned URL; the *inline* document read is a separate, existing path.
  Do not conflate them.
- **Do not re-parse the SBOM** to build the table — the document already carries the enrichment; read it.

### Testing standards

- A test asserting the default view is the component table and the default sort matches Story 8.16.
- A test asserting the raw view is not present in the initial tab response.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.13: SBOM Viewer Tab]
- `frontend/src/components/SbomTab.tsx`, `frontend/src/api/sbom.ts`,
  `generate_sbom/sbom/{document,views,selectors}.py`.
- Upstream: `21-12-results-page-shell-and-overview-tab.md`. Downstream: `21-17` (its Excel export).

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. Backend **680 passed**, coverage **96.44%**; frontend **223 passed**.
- **16 new tests** in `tests/unit/test_sbom_tab.py`; route `ui-job-sbom-raw` →
  `/results/<task_id>/sbom/raw`.
- AC #4 asserted directly: `bomFormat` and `specVersion` — strings that exist only in the raw
  JSON — are **absent** from the tab's payload while the raw endpoint is reachable from it.
- Default sort verified by character position (`alpha` before `zeta`); `?sort=-name` reverses it
  and two identical requests produce identical output.
- Oversized document: a >2 MB body renders the download affordance and **no** document text.
- Unavailable covered three ways: purged job, deleted blob with the key still set, and the raw
  endpoint — all render the notice.

### Completion Notes List

**The document read is now shared with the API, not duplicated.** `SbomDocumentView` had the
storage read, existence checks and parsing inline. Extracted to
`selectors.read_inline_document`, which returns an `InlineDocument` or `None`; the DRF endpoint
and the tab both call it. The existing document tests (46) passed unchanged, so the API's
behaviour is intact — this is the same pattern Story 21.9 used for `submit_job`.

**"Unavailable" is one condition, deliberately.** Never produced, not finished, and purged all
collapse to `None`, because the viewer's response is identical in all three cases — the SPA's
own comment says "an unavailable/expired artifact shows a notice, not an error". A test covers
the nastiest variant: the row still carries a `result_key` but the blob is gone, which is the
real post-purge race, and it renders the notice rather than raising.

**The raw view's size risk is handled by keeping it out of the payload *and* capping it.** Two
separate protections, because they solve different problems: its own endpoint means a large
document never slows the component table, and the 2 MB cap means asking for the raw view of a
huge SBOM offers the presigned download instead of freezing the browser with megabytes of text
in a `<pre>`. The Dev Notes flagged this as "the size risk" and permitted exactly this.

**The two document paths are kept distinct, as the Dev Notes require.** The inline read (AD-5)
serves the viewer; the download is the existing presigned 303 (AD-11) and is only ever linked,
never proxied. The oversized branch links at the download endpoint rather than streaming.

**The SBOM is not re-parsed to build the table.** The enrichment — licence (8.25), ecosystem
and purl type (8.26), direct/transitive (8.3-8.4) — was written into the document at generation
time and is read back through `normalize_components`. A test asserts each of those columns
renders real values.

**The Relationship column hides itself when empty,** mirroring the SPA's `showRelationship`:
relationship data only exists where resolution captured it, and a column of em dashes is worse
than no column. Tested both ways.

**Sorting moved server-side and is now linkable.** `RequestConfig` applies `?sort=` and the
default is `name` ascending (Story 8.16). The trade — a round trip per sort — was accepted when
the epic was scoped; the gain is that a sorted view survives being shared, which the SPA's
in-browser sort could not do.

**A test of mine was initially wrong about the data, not the code.** My fixture emitted a
`package:relationship` property; the parser reads `sbom:relationship`. The failure was in the
test document, and finding it required reading `document.py` rather than adjusting the
assertion — worth noting because the enrichment property names are not guessable.

**One 21.12 test narrowed, as expected.** `test_placeholder_tabs_are_neutral_not_errors`
iterated all four detail tabs; `sbom` is now real. The list is narrowed with a comment saying
each of 21.14-21.16 will narrow it further as it lands.

**Not done here.** The Excel export of components is Story 21.17 (server-side openpyxl),
explicitly not this story. There is no client-side filtering or pagination of the component
table — the SPA had neither, and adding it would have exceeded parity.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story), and the four deferred pluggability violations.

### File List

**New (2)**
- `src/django_apps/inventory/templates/inventory/sbom/tabs/_sbom_raw.html`
- `tests/unit/test_sbom_tab.py` (16 tests)

**Modified (6)**
- `src/django_apps/inventory/sbom/selectors.py` — `InlineDocument`, `read_inline_document`
- `src/django_apps/inventory/sbom/views.py` — `SbomDocumentView` now uses the shared reader
- `src/django_apps/inventory/sbom/tables.py` — `SbomComponentTable`
- `src/django_apps/inventory/sbom/pages.py` — `sbom_tab_context`, `SbomRawView`,
  `RAW_INLINE_MAX_BYTES`
- `src/django_apps/inventory/templates/inventory/sbom/tabs/_sbom.html` — the real tab
- `src/django_apps/inventory/urls_pages.py` — `ui-job-sbom-raw`
- `tests/unit/test_results_page.py` — placeholder list narrowed
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Filled in the SBOM viewer tab: a django-tables2 component table carrying the licence, ecosystem, and direct/transitive enrichment already embedded in the document, with server-side sorting defaulting to name ascending, and a raw-document view behind a toggle. The raw document is fetched by its own endpoint so it never rides along in the tab's payload, and above a 2 MB cap it offers the presigned download instead of inlining megabytes of text. The storage read and parsing were extracted so the DRF endpoint and the tab share one implementation. An unavailable or purged artifact renders a notice, never an error. `pixi run ci` exit 0; 680 backend tests at 96.44%. |
