# Story 8.26: Include Ecosystem (PyPI/Conda) in the SBOM Document

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Reopened enrichment of Epic 8** (mirrors Story 8.25's license-embedding). `PackageSpec.ecosystem`
> (`pypi`/`conda`, Story 8.8) is already captured at resolution but is **not written into the generated
> SBOM document** — the same gap license was in before 8.25. This story embeds it.
>
> **This story is a hard prerequisite for Story 16.3** (Consolidated de-duplicated SBOM by Application ID):
> 16.3 dedupes components read back from the **stored** SBOM documents by `(name, version, ecosystem)`, so
> ecosystem must be present *in the persisted document* for the dedupe key to distinguish a PyPI package from
> a conda package of the same name/version. Build 8.26 before 16.3.

## Story

As a user reading (or consuming) the SBOM document,
I want each component to carry its ecosystem (PyPI or conda),
so that the ecosystem is an explicit, queryable field in the stored SBOM — visible where useful and available
as a dedupe key for the consolidated-SBOM feature (Story 16.3).

## Acceptance Criteria

1. **Every component in the generated SBOM carries its ecosystem.**
   Given a resolved `PackageSpec` with `ecosystem` ∈ {`pypi`, `conda`} (Story 8.8),
   when Phase 3 generates the SBOM document, then that component records the ecosystem —
   CycloneDX: a component property `package:ecosystem` (mirroring the existing `sbom:relationship`
   property, `generation.py:120`) **and** a `purl` whose type reflects the ecosystem
   (`pkg:pypi/...` vs `pkg:conda/...`); SPDX: the package `purl` type likewise reflects the
   ecosystem. This holds for the default `cdx-json` output and for `cdx-xml` and `spdx-2.3`.
2. **The purl type is correct per ecosystem — the hardcoded `pkg:pypi` is fixed.**
   Given a conda-tagged package, when the SBOM is generated, then its purl is `pkg:conda/<name>@<version>`
   (not `pkg:pypi/...`). The SPDX path currently hardcodes `pkg:pypi/{name}@{version}`
   (`generation.py:188`) and CycloneDX sets **no** purl at all today (`generation.py:114-125`) — both are
   corrected so the purl type is derived from `pkg.ecosystem`.
3. **Unknown/absent ecosystem degrades gracefully — no crash.**
   Given a spec whose ecosystem is missing or an unexpected value, when the SBOM is generated, then the
   component still emits (falls back to the `pypi` default, consistent with `PackageSpec.ecosystem`'s default,
   `_types.py:30`) and generation never raises.
4. **The ecosystem round-trips through `document.py`.**
   Given the enriched SBOM document, when it is parsed back by `sbom/document.py::normalize_components`,
   then each returned component dict carries an `ecosystem` field (read from the `package:ecosystem`
   property and/or the purl type) alongside the existing `name/version/type/purl/license/relationship`
   (`document.py:203-215`). Where useful, surface it in the SBOM tab (the Components table already reads the
   normalized dict — add an ecosystem column/badge only if it fits the existing table; optional for the core
   AC, which is the round-trip).
5. **AD-6 preserved.**
   Given the storage triad (AD-6, memory `phase3-writes-blob-not-phase8`), when the ecosystem is added, then
   it is written into the SBOM **at Phase 3 generation time** (the phase that already writes the blob) — the
   persisted blob is not rewritten downstream, Phase 8 (`persist_artifacts`) still only finalizes the DB, and
   no blob flows through the Celery result backend. `PackageSpec.ecosystem` is already threaded to Phase 3
   (Story 8.8 — analysis re-resolves via `resolve_job_packages`), so no new chain-payload plumbing is needed.
6. **Tested; CI green.**
   Backend unit test: a generated CycloneDX document's components carry `package:ecosystem` and the correct
   purl type for both a pypi and a conda package; the SPDX path sets the correct purl type; an unknown
   ecosystem falls back to `pypi` without raising. Round-trip test: `normalize_components` returns the
   ecosystem for all three formats. Frontend test (only if a column is added): the SBOM Components table
   renders the ecosystem. `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Emit the ecosystem on each component at Phase 3 (AC: #1, #2, #3)**
  - [ ] **CycloneDX** (`backend/generate_sbom/sbom/generation.py:114-125`): on each `Component`, add a
    `Property(name="package:ecosystem", value=pkg.ecosystem)` (mirroring the `sbom:relationship` property
    already set at `:120`), and set a `purl` (`PackageURL` / `cyclonedx.model.PackageURL` or a `pkg:` string)
    whose type is `pkg.ecosystem` — `pkg:conda/<name>@<version>` for conda, `pkg:pypi/...` for pypi. Today
    CycloneDX sets no purl (`:114-125`) — add it. Fall back to `pypi` for an empty/unknown ecosystem (AC #3).
  - [ ] **SPDX** (`backend/generate_sbom/sbom/generation.py:188`): replace the hardcoded
    `entry.set_purl(f"pkg:pypi/{pkg.name}@{pkg.version}")` with a purl whose type is derived from
    `pkg.ecosystem`. Optionally set an SPDX external ref / annotation for the ecosystem if the CycloneDX
    property has no clean SPDX analogue — but the purl type is the primary, required carrier for SPDX.
  - [ ] Keep `generation.generate_sbom_document(...)` **pure / I/O-free** (Story 3.4) — `PackageSpec.ecosystem`
    is already on the specs passed in (Story 8.8), so no fetch is needed; just read `pkg.ecosystem`.
- [ ] **Task 2 — Parse the ecosystem back out (AC: #4)**
  - [ ] `sbom/document.py::normalize_components` / `_component` (`:18`, `:203-215`): add an `ecosystem` key to
    the returned dict, read from the `package:ecosystem` property (CycloneDX JSON + XML) / SPDX annotation, and
    fall back to parsing the purl type (`pkg:<type>/...`) so it works even for older stored documents that
    predate this story (graceful default `pypi`). Add the parse for all three format branches
    (`_cyclonedx` JSON, `_cyclonedx_xml`, `_spdx`).
- [ ] **Task 3 — Surface it where useful (AC: #4, optional)**
  - [ ] If it fits cleanly, add an ecosystem column/badge to the SBOM tab Components table
    (`frontend/src/components/SbomTab.tsx`, `frontend/src/api/sbom.ts` `SbomComponent` type) reading the new
    `ecosystem` field. Optional — the load-bearing AC is the round-trip (Task 2), which 16.3 depends on. If a
    badge already distinguishes pypi/conda elsewhere (Story 8.9's registry links), keep it consistent.
- [ ] **Task 4 — Tests (AC: #6)**
  - [ ] Backend unit (`backend/tests/unit/test_sbom_generation.py`): with specs tagged `pypi` and `conda`,
    assert generated CycloneDX components carry `package:ecosystem` and the correct purl type; assert the SPDX
    path sets the correct purl type; assert an unknown/blank ecosystem falls back to `pypi` and does not raise.
  - [ ] Backend unit (`backend/tests/unit/test_sbom_document.py`): `normalize_components` returns the
    `ecosystem` for a CycloneDX-JSON, a CycloneDX-XML, and an SPDX document (incl. purl-type fallback for a
    doc with no `package:ecosystem` property).
  - [ ] Frontend (only if Task 3 adds a column): `SbomTab.test.tsx` renders the ecosystem.
  - [ ] `pixi run ci` green.

## Dev Notes

### Why this story exists (the gap)

`PackageSpec.ecosystem` (`pypi`/`conda`) is captured at resolution (Story 8.8, `_types.py:16-30`) and reaches
the version-currency report, but the **generated SBOM document never records it** — exactly the situation the
per-component license was in before Story 8.25. Worse, the SPDX purl is **hardcoded** to `pkg:pypi/...`
(`generation.py:188`), so a conda package is mislabeled in the document, and CycloneDX sets no purl at all
(`generation.py:114-125`). This story writes the ecosystem into the document (property + correct purl type)
and parses it back in `document.py`, mirroring 8.25's shape.

### Why 16.3 needs it (the dependency)

Story 16.3 builds one consolidated, de-duplicated SBOM per Application ID by reading the **stored** SBOM
documents of the completed jobs and unioning + deduping their components. The dedupe identity is
**(name, version, ecosystem)** — pypi and conda of the same name/version are kept **distinct** (product
decision). That key is only computable if ecosystem is present in the stored document. So 8.26 must land
before 16.3. Build order: **16.1 → 16.2 → 8.26 → 16.3 → 16.4**.

### AD-6 (Phase 3 writes the blob) — same rule as 8.25

The ecosystem is written into the SBOM **at Phase 3 generation** (the phase that already writes the blob to
`result_key`, `tasks/sbom_pipeline.py`), not rewritten downstream. Unlike 8.25's license (which needed a PyPI
fetch), ecosystem is already on the `PackageSpec` handed to the pure serializer — so this is purely a
serialization + parse-back change with **no new I/O** and no chain-payload plumbing (AD-6 preserved). If any
implementation detail seems to require Phase 8 rewriting the blob, STOP and raise it (memory
`phase3-writes-blob-not-phase8`).

### CycloneDX vs SPDX representation

- **CycloneDX** already uses component `Property` entries (`sbom:relationship`, `generation.py:120`); add
  `package:ecosystem` the same way. Set the purl via `PackageURL` with `type=pkg.ecosystem`. `document.py`
  already parses properties back (the relationship path) and parses `purl` (`document.py:207,215,286-287`),
  so extending it for ecosystem is a small, symmetric change.
- **SPDX** carries the purl as an external ref; fix the hardcoded type at `generation.py:188`. SPDX has no
  first-class "property" like CycloneDX, so the purl type is the primary carrier; add an annotation only if
  the round-trip needs a second signal.

### Project Structure Notes

- Generation: `backend/generate_sbom/sbom/generation.py` — CycloneDX components `:114-125` (add property +
  purl), SPDX `:188` (fix purl type). Purity per Story 3.4 (read `pkg.ecosystem`, no fetch).
- Parse-back: `backend/generate_sbom/sbom/document.py` — `normalize_components`/`_component` `:18,203-215`,
  purl parse `:286-287`; add an `ecosystem` key across the three format branches.
- Source field: `backend/generate_sbom/sbom/parsers/_types.py:16-30` (`PYPI`/`CONDA`, `ecosystem` default).
- Optional UI: `frontend/src/components/SbomTab.tsx`, `frontend/src/api/sbom.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.26: Include Ecosystem in the SBOM Document]
- Generation: `backend/generate_sbom/sbom/generation.py:114-125` (CycloneDX component), `:188` (SPDX purl)
- Parse-back: `backend/generate_sbom/sbom/document.py:18,203-215,286-287`
- Ecosystem source: `backend/generate_sbom/sbom/parsers/_types.py:16-30`
- AD-6 / phase split: memory `phase3-writes-blob-not-phase8`; Story 3.4 completion notes
- Precedent (same enrichment shape): `8-25-include-license-in-sbom-document.md`
- Ecosystem capture: `8-8-capture-package-ecosystem-pypi-conda.md`
- **Enables:** `16-3-consolidated-sbom-by-application-id.md` (dedupe key requires ecosystem in the document)

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Claude Opus 4.8, 1M context)

### Debug Log References

- Initial SPDX ecosystem test hit `StopIteration`: the root application package carries a `vcs`
  external ref but no `purl`, so a naive `next(... referenceType == "purl")` over every package with
  `externalRefs` raised. Fixed by reusing the existing `_spdx_purl` helper in the test.

### Completion Notes List

- CycloneDX (`generation.py`): each library `Component` now sets `purl=PackageURL(type=<ecosystem>, ...)`
  (previously no purl) and adds a `package:ecosystem` property mirroring `sbom:relationship`.
- SPDX (`generation.py`): the hard-coded `pkg:pypi/...` purl is replaced with `pkg:<ecosystem>/...`
  (correctness fix — conda packages were mislabeled pypi).
- `_purl_ecosystem` normalizes empty/unexpected ecosystem values to `pypi` (AC #3) so generation never raises.
- Round-trip (`document.py`): `normalize_components` returns an `ecosystem` key for all three formats,
  read from the `package:ecosystem` property (CycloneDX JSON + XML) and falling back to the purl type
  (`pkg:<type>/...`), then to `pypi`, so older stored documents still resolve an ecosystem.
- Frontend: `SbomComponent` gains `ecosystem: string | null`; the SBOM tab Components table renders an
  Ecosystem column.
- AD-6 preserved: purely a serialize + parse-back change at Phase 3; no new I/O, no downstream blob rewrite.

### File List

- backend/generate_sbom/sbom/generation.py
- backend/generate_sbom/sbom/document.py
- backend/tests/unit/test_sbom_generation.py
- backend/tests/unit/test_sbom_document.py
- frontend/src/api/sbom.ts
- frontend/src/components/SbomTab.tsx
- frontend/src/components/SbomTab.test.tsx
