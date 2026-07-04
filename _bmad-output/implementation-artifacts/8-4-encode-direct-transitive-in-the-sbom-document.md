# Story 8.4: Encode Direct/Transitive in the SBOM Document

Status: ready-for-dev

<!-- Contexted from the 8.2 spike: planning-artifacts/research/direct-vs-transitive-design.md -->

## Story

As a user,
I want the generated SBOM to carry the direct/transitive relationship,
so that any consumer of the SBOM — not just this app — can tell them apart.

## Acceptance Criteria

1. Given a CycloneDX (JSON or XML) output, when the SBOM is generated, then only the **direct** components are registered as dependencies of the root metadata component (not "root depends on everything"), and each component carries a `sbom:relationship` property with value `direct`, `transitive`, or `unknown`.
2. Given an SPDX (JSON) output, when the SBOM is generated, then the root package `DEPENDS_ON` each **direct** package via an SPDX relationship; transitive packages are listed without a root `DEPENDS_ON` edge.
3. Given a job whose packages are all `unknown` (e.g. from `pixi.lock`), when the SBOM is generated, then it falls back to the prior behavior (no misleading direct/transitive split) and remains valid.
4. Given any generated SBOM, when it is validated against its standard's schema, then it remains schema-valid (the relationship encoding does not break conformance).
5. Given the SBOM viewer's `normalize_components` (Story 8.6), when it parses a document produced by this story, then the component's `relationship` is populated (lighting up the viewer's Relationship column).

## Tasks / Subtasks

- [ ] Task 1 — CycloneDX encoding (AC: #1, #3, #4)
  - [ ] In `generation._generate_cyclonedx`, split components by `relationship`; `bom.register_dependency(root, direct_components)` (fall back to all components when none are `direct`/all `unknown`)
  - [ ] Add `Property(name="sbom:relationship", value=pkg.relationship)` to each component
- [ ] Task 2 — SPDX encoding (AC: #2, #3, #4)
  - [ ] In `generation._generate_spdx`, add an SPDX relationship: root package `DEPENDS_ON` each direct package (`lib4sbom` relationship API); leave transitive/unknown without a root edge
- [ ] Task 3 — Viewer parser (AC: #5)
  - [ ] Update `sbom/document.py::normalize_components` to read the relationship back out — CycloneDX from the `sbom:relationship` property (JSON + XML), SPDX from the root `DEPENDS_ON` set — so the viewer column populates
- [ ] Task 4 — Tests
  - [ ] Per format: direct components are root dependencies; transitive/unknown are not; property/relationship present
  - [ ] Schema-validity per format (parse back / validate)
  - [ ] `normalize_components` round-trips `relationship` for each format
  - [ ] `pixi run ci` exits 0 with ≥90% coverage

## Dev Notes

### Encoding (from the 8.2 spike)

We have a flat list + a per-package flag (not a full edge graph) at generation time,
so encode what's truthful — the app's *direct* dependencies:

- **CycloneDX:** `register_dependency(root, direct_components)` + a component
  `sbom:relationship` property (mirrors the provenance properties already emitted).
- **SPDX:** root package `DEPENDS_ON` each direct package.

Both are schema-valid; a future annotation-parsing enhancement (8.2 Decision 1
secondary) could enrich these from root→direct to the full tree without changing
this contract. [Source: research/direct-vs-transitive-design.md#Decision 3]

### Current generators

`generation.py::_generate_cyclonedx` already does `bom.register_dependency(root,
components)` (all) and emits root properties — the change is to pass only direct
components and add a per-component property. `_generate_spdx` builds a package dict;
add relationships from the root. [Source: backend/generate_sbom/sbom/generation.py]

### Dependency on 8.3

Requires `PackageSpec.relationship` (Story 8.3). Until 8.3 lands, all packages are
`unknown` and AC #3's fallback applies.

### References

- [Source: _bmad-output/planning-artifacts/research/direct-vs-transitive-design.md#Decision 3]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.4]
- [Source: backend/generate_sbom/sbom/generation.py]
- [Source: backend/generate_sbom/sbom/document.py — normalize_components (8.6)]
- [Source: prd.md#FR-4.4]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
