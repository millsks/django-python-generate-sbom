# Story 8.11: SBOM Metadata Block — Document Ordering & Viewer Display

Status: review

## Story

As a user,
I want the SBOM's metadata shown above the component table (and placed first in the document itself),
so that I can see the provenance and document info before scanning the components.

## Acceptance Criteria

1. Given the SBOM viewer's **Components** view, when it renders, then a metadata block appears **above** the component table showing the document metadata — at minimum: component name, application id, repository URL, source branch (the provenance), the format/spec version, and the generated timestamp (FR-E9).
2. Given the SBOM document is generated, when it is serialized, then the `metadata` key and its data are placed **before** the component data in the document (CycloneDX `metadata` precedes `components`; SPDX document/creation info precedes `packages`).
3. Given the content endpoint (`/sbom/document/{task_id}/`), when it returns, then it includes a parsed `metadata` object (provenance + format + timestamp) alongside `components` and `raw`, so the viewer needs no client-side SBOM parsing.
4. Given the **Raw** view, when shown, then the raw document already leads with the metadata (AC #2) — no separate change needed there.
5. Given a document with missing/partial metadata, when the block renders, then absent fields are omitted gracefully (no blank/broken rows).

## Tasks / Subtasks

- [ ] Task 1 — Document ordering (AC: #2)
  - [ ] Confirm/adjust `generation.py` so the serialized SBOM leads with `metadata` before `components` for CycloneDX (JSON + XML) and SPDX; add a generation test asserting metadata precedes components in the output
- [ ] Task 2 — Metadata in the content endpoint (AC: #3, #5)
  - [ ] Extend `sbom/document.py` to parse a `metadata` dict (component name, the four provenance fields from CycloneDX properties / SPDX comment, `format`, spec version, generated timestamp) and return it from `SbomDocumentView`
- [ ] Task 3 — Viewer metadata block (AC: #1, #4, #5)
  - [ ] In `SbomTab.tsx`, render a metadata summary (MUI card / definition list) above the component table in the Components view; omit absent fields
  - [ ] Add `metadata` to the `SbomDocument` type in `api/sbom.ts`
- [ ] Task 4 — Tests
  - [ ] Backend: metadata parsed for cdx-json/xml + spdx; ordering test
  - [ ] Frontend: metadata block renders the provenance fields; missing fields omitted
  - [ ] `pixi run ci` exits 0

## Dev Notes

### Provenance is already embedded

`generation.py` already writes the four provenance fields — CycloneDX as root-component `Property`s (`application:id`, `vcs:branch`) + a VCS external reference, SPDX as a package comment (`application:id=...; vcs:branch=...`). Task 2 reads these back out into the `metadata` object; no new capture needed. [Source: backend/generate_sbom/sbom/generation.py]

### Ordering

CycloneDX JSON schema orders `metadata` before `components` already in most serializers — Task 1 verifies and locks it with a test (assert the `metadata` key/offset precedes `components`). SPDX: creation/document info precedes `packages`. If a serializer emits a different order, post-process the dict ordering before writing.

### References

- [Source: frontend/src/components/SbomTab.tsx, frontend/src/api/sbom.ts]
- [Source: backend/generate_sbom/sbom/document.py, generation.py, views.py (SbomDocumentView)]
- [Source: _bmad-output/implementation-artifacts/8-6-in-app-sbom-viewer-tab.md]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

- `pixi run ci` → exit 0: backend 252 passed (coverage 93.89%, gate 90%), frontend 56 passed, build green.

### Completion Notes List

- Task 1 (AC #2): CycloneDX XML and SPDX already lead with metadata/creation info before components/packages; only CycloneDX **JSON** emitted `metadata` after `components`, so `generation._order_metadata_before_components` reorders the top-level JSON keys so `metadata` precedes `components`. A parametrized generation test asserts the metadata marker precedes the component marker for all three formats.
- Task 2 (AC #3, #5): added `document.parse_metadata(raw, output_format)` which reads back the already-embedded provenance (CycloneDX root-component `application:id`/`vcs:branch` properties + VCS external reference; SPDX root-package comment + external ref) plus component name, human format name, spec version (CycloneDX `specVersion` / namespace, SPDX `spdxVersion` minus the `SPDX-` prefix), and generated timestamp (CycloneDX `metadata.timestamp`, SPDX `creationInfo.created`). Absent/empty fields are dropped so the endpoint omits them. `SbomDocumentView` now returns `metadata` alongside `format`, `components`, `raw`.
- Task 3 (AC #1, #4, #5): `SbomTab` renders a metadata definition-list block (`aria-label="SBOM metadata"`) above the component table in the Components view, showing only present fields; format+spec version combine into one line (e.g. "CycloneDX 1.6"). Added `SbomMetadata` (all-optional) to the `SbomDocument` type. The Raw view is unchanged and already leads with metadata via AC #2.
- Task 4: backend tests cover metadata parsing for cdx-json/cdx-xml/spdx, omission of absent fields, unknown-format empty dict, ordering, and the endpoint returning metadata; frontend tests cover the block rendering provenance, omitting absent fields, and rendering nothing when metadata is absent.

### File List

- backend/generate_sbom/sbom/generation.py (metadata-before-components JSON reorder)
- backend/generate_sbom/sbom/document.py (new `parse_metadata` + helpers)
- backend/generate_sbom/sbom/views.py (`SbomDocumentView` returns `metadata`)
- backend/tests/unit/test_sbom_document.py (metadata + ordering tests)
- frontend/src/api/sbom.ts (`SbomMetadata` type + `metadata` on `SbomDocument`)
- frontend/src/components/SbomTab.tsx (metadata block above the table)
- frontend/src/components/SbomTab.test.tsx (metadata block tests)
