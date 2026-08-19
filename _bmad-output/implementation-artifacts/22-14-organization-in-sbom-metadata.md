---
baseline_commit: 316bb7f
---

# Story 22.14: Carry the Organization Into the SBOM Metadata

Status: review

## Story

As a consumer of a generated SBOM,
I want the document to name the organization it was produced for,
so that the field saying *whose* software this describes is in the artifact, not only in the app.

**Context:** Product-owner direction: *"the orgs are selected in the upload form and should be added to the
sbom with the other metadata."* The upload form has chosen the organization since Story 21.9, but the choice
went no further than the `SBOMJob` row. FR-3.8's four provenance fields were embedded; the fifth, and
arguably the most consequential for a line-of-business inventory, was not.

## Acceptance Criteria

1. **`Provenance` carries the organization**, lifted from the manifest's own `org` rather than from the
   acting request — the document must say which tenant the job was *filed against*, even when it is
   regenerated or exported later by someone acting elsewhere.
2. **It is emitted in each format's own supplier slot**, not as a custom property: CycloneDX
   `metadata.supplier`, SPDX `PackageSupplier`.
3. **The existing four provenance fields are untouched.**
4. **A missing or awkward name cannot cost the document.** Generation is a hard-fail phase (FR-4.5), so an
   empty organization still produces a document, and a name containing markup still produces well-formed XML.
5. **Gate green.**

## Tasks / Subtasks

- [x] **Task 1 — Write the failing tests first (AC: all)** — `tests/unit/test_sbom_organization_metadata.py`
- [x] **Task 2 — Add `organization` to `Provenance` (AC: #1)**, defaulting to empty
- [x] **Task 3 — CycloneDX supplier (AC: #2)** — `OrganizationalEntity` on `bom.metadata.supplier`
- [x] **Task 4 — SPDX supplier (AC: #2)** — `root.set_supplier("Organization", …)`
- [x] **Task 5 — `build_provenance` reads `manifest.org.name` (AC: #1)**
- [x] **Task 6 — Gate (AC: #5)**

## Dev Notes

### Why the supplier field and not a property

The four existing fields are emitted as custom properties (`application:id`, `vcs:branch`) because
CycloneDX has no standard slot for them. It *does* have one for the supplier, and so does SPDX. A
`Property(name="organization")` would be legible only to this application, which defeats the point of
producing a standard document — the supplier is a field other SBOM tooling already reads.

### Traps

- **`generate_sbom_document(packages, output_format, provenance)`** — the format is the *second*
  positional argument, not the third. Getting it wrong raises `Unknown output format: Provenance(...)`.
- **The XML serializer is a separate code path**, not a re-encoding of the JSON. Assert both.
- **`manifest.org_id` before `manifest.org.name`** — a manifest with no org would otherwise raise inside a
  hard-fail phase.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- 9 new tests; all 9 **failed first** (`Provenance.__init__() got an unexpected keyword argument`).
- `pixi run ci` — **exit 0**.

### Completion Notes List

**The end-to-end test is the one that matters.** The generator units prove a `Provenance` becomes a
supplier; they cannot catch `build_provenance` reading the *acting* org instead of the manifest's, which
would leave every unit green and stamp every real SBOM with the wrong tenant. A second org is created in
that test purely so a mix-up would be visible.

**Two hostile inputs are covered because generation is a hard-fail phase.** An empty name and a name
containing `&` and `<>`: the first must not cost the document, the second must not produce XML no consumer
can parse — a corrupted artifact being the worse of the two failures, since it looks like success.

### File List

**New (1)**
- `tests/unit/test_sbom_organization_metadata.py` (9 tests)

**Modified (2)**
- `src/django_apps/inventory/sbom/generation.py` — `Provenance.organization`, both serializers
- `src/django_apps/inventory/sbom/services.py` — `build_provenance`

## Change Log

| Date | Change |
|---|---|
| 2026-08-19 | The organization chosen on the upload form is now written into the generated SBOM as its **supplier** — CycloneDX `metadata.supplier`, SPDX `PackageSupplier` — rather than as a custom property only this app could read. Taken from the manifest's own org so a regenerated or later-exported document still names the tenant the job was filed against. Empty names and names containing markup are both covered, because SBOM generation is a hard-fail phase. |
