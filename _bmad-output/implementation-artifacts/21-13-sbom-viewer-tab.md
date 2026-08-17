# Story 21.13: SBOM Viewer Tab

Status: ready-for-dev

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

- [ ] **Task 1 — Component table (AC: #1, #2, #3)** — django-tables2; server-side ordering; all enrichment
  columns.
- [ ] **Task 2 — Raw view (AC: #1, #4)** — Separate htmx-loaded partial or a streamed response; not part of
  the tab's initial payload.
- [ ] **Task 3 — Toggle (AC: #1)** — Segmented control; component table is the default.
- [ ] **Task 4 — Unavailable state (AC: #5)**.
- [ ] **Task 5 — Tests + gate (AC: #6)**.

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

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
