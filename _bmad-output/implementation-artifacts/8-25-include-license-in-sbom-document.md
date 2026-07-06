# Story 8.25: Include License in the SBOM Document

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user reading the SBOM Results page,
I want each component in the generated SBOM document to carry its license,
so that the SBOM tab's Components table License column (and the raw SBOM blob) show the license instead of "—", matching what the Licenses tab already reports.

## Acceptance Criteria

1. **Every component in the generated SBOM carries its license (when determinable).**
   Given a resolved package whose license can be determined from PyPI metadata,
   when Phase 3 generates the SBOM document, then that component carries the license —
   CycloneDX 1.6: `component.licenses` (an SPDX license id, an SPDX expression, or a
   named `License` for a non-SPDX/free-text value); SPDX 2.3: the package's
   `licenseConcluded`/`licenseDeclared`. This holds for the default `cdx-json` output
   and for `cdx-xml` and `spdx-2.3` (FR-E5, extends FR-4.4).
2. **Unknown/absent licenses degrade gracefully — no crash.**
   Given a package whose license cannot be determined (no metadata, non-classifiable
   free text, or a PyPI fetch failure), when the SBOM is generated, then the component
   is emitted with no license entry (CycloneDX) / `NOASSERTION` (SPDX) and generation
   never raises — the SBOM still builds for the rest of the packages.
3. **The SBOM tab Components table and the Raw blob both show the license.**
   Given the enriched SBOM document, when the SBOM tab loads, then the License column
   populates from the document (via the existing `sbom/document.py::normalize_components`
   → `SbomTab` path — no viewer change required) and the raw view shows the same license
   inside the document text.
4. **The SBOM license matches the Licenses tab — one normalization, no divergence.**
   Given the same package, when its license appears in both the SBOM document and the
   Licenses tab, then both are produced by the **same** license-resolution/SPDX-mapping
   used by the Phase 5 compliance report (`_extract_license`) — the SBOM must not use a
   second, divergent mapping.
5. **AD-6 preserved.**
   Given the storage triad (AD-6), when the license is added, then it is written into the
   SBOM **at Phase 3 generation time** (the phase that already writes the blob) — the
   persisted blob is not rewritten downstream, Phase 8 (`persist_artifacts`) still only
   finalizes the DB, and no blob flows through the Celery result backend. (If, during
   implementation, this boundary cannot hold, STOP and raise it — do not silently make
   Phase 8 rewrite the blob.)
6. **Tested; CI green.**
   Backend unit test: a generated CycloneDX document's components include `licenses` for
   packages with a known license and omit it cleanly for unknown ones (and the SPDX path
   sets `licenseConcluded`/`NOASSERTION`). Frontend test: the SBOM Components table renders
   a component's license and shows `—` for a null-license component. `pixi run ci` green.

## Tasks / Subtasks

- [ ] **Task 1 — Share the Phase 5 license normalization (AC: #4)**
  - [ ] Promote the per-package resolver `_extract_license(session, pkg) -> str | None`
    (`backend/generate_sbom/analysis/services/license.py:71-90`) — plus the
    `_CLASSIFIER_SPDX` table (`license.py:50-68`) — into a single reusable normalization
    that BOTH the Phase 5 report and Phase 3 generation call. Keep the resolution
    precedence identical (PEP 639 `license_expression` → Trove `classifiers`→SPDX → short
    free-text `license`). `classify()` (`license.py:111-125`) must keep using the exact
    same function so the two outputs cannot diverge (AC #4).
  - [ ] **Placement / layering:** prefer extracting the pure normalization (function +
    SPDX table) into a neutral module both sides import, rather than importing
    `analysis.services.license` from `sbom/generation.py`. Verify no import cycle
    (`analysis.services.license` already imports `PackageSpec` from `sbom.parsers._types`
    and `http` from `analysis.services`). One shared source is the invariant; the exact
    module is dev's call.
- [ ] **Task 2 — Build a license map in the Phase 3 task, keep generation I/O-free (AC: #1, #2, #5)**
  - [ ] In the Phase 3 task `generate_sbom_document` (`backend/generate_sbom/tasks/sbom_pipeline.py:144-176`),
    before calling the pure serializer (`:159`), resolve a license map over the resolved
    packages using the shared normalizer and the cached `http.pypi_session()`
    (`backend/generate_sbom/analysis/services/http.py:84-89`; 1h cache, 5 req/s). Phase 3
    warms the cache; Phase 5's later `classify` fetch hits it — no doubled external load.
  - [ ] Keep `generation.generate_sbom_document(...)` **pure / I/O-free** (Story 3.4
    completion note) by passing the resolved license map IN as a parameter
    (e.g. `license_map: dict[tuple[str, str], str | None]` keyed by `(name, version)`),
    not by fetching inside the serializer. This preserves the independently-testable
    contract and lets the AC #6 unit test drive it with a fixture map (no network).
- [ ] **Task 3 — Emit the license on each component (AC: #1, #2)**
  - [ ] **CycloneDX** (`backend/generate_sbom/sbom/generation.py:97-106`): after building each
    `Component(...)`, set `component.licenses` from the map. Use
    `cyclonedx-python-lib`'s `LicenseFactory().make_from_string(value)`
    (`cyclonedx.factory.license`) so a known SPDX id → `SpdxLicense`, an SPDX expression →
    `LicenseExpression`, and any other non-empty string → a named `License` — the correct
    CycloneDX 1.6 representation for each case. For a `None`/empty value add nothing (AC #2).
  - [ ] **SPDX** (`backend/generate_sbom/sbom/generation.py:160-172`): on each `SBOMPackage`,
    call `set_licenseconcluded(value)` and `set_licensedeclared(value)` for a known value,
    else `NOASSERTION` (AC #2). `document.py::_spdx_license` reads
    `licenseConcluded`/`licenseDeclared`, so this surfaces in the viewer.
- [ ] **Task 4 — Confirm the viewer surfaces it (AC: #3)**
  - [ ] No SBOM-viewer change is expected: `sbom/document.py::normalize_components` already
    parses `licenses` back out (`_component` `document.py:203-218`, `_cyclonedx_license`
    `:248-263`, `_spdx_license` `:361-367`), and `SbomTab.tsx:153` renders `row.license ?? '—'`
    from `SbomComponent.license` (`frontend/src/api/sbom.ts:6-13`). Verify end-to-end that
    an enriched document yields a populated License column and Raw view.
- [ ] **Task 5 — Tests (AC: #6)**
  - [ ] Backend unit (`backend/tests/unit/test_sbom_generation.py`): with a fixture
    `license_map`, assert the generated CycloneDX components carry `licenses` for
    known-license packages (SPDX id, expression, and free-text/name cases) and carry none
    for an unknown one; assert the SPDX path sets `licenseConcluded` for a known value and
    `NOASSERTION` for an unknown one. No network.
  - [ ] Backend unit (`test_license_service.py` / shared-normalizer test): assert the shared
    resolver still yields the same values Phase 5 relied on (parity guard for AC #4).
  - [ ] Frontend (`frontend/src/components/SbomTab.test.tsx`): the existing `DOC` fixture
    already has a `license: 'BSD-3-Clause'` row (asserted) and a `license: null` row — add
    the missing assertion that the null-license row renders `—` (the column reads
    `row.license`), so the em-dash-for-all regression is caught.
  - [ ] `pixi run ci` green.

## Dev Notes

### Why this story exists (the gap)

On the SBOM Results page the **SBOM tab → Components** table shows a License column that is
`—` for every package, while the **Licenses tab** correctly shows each package's license.
The two read the **same-named `license` field from different sources**: the Licenses tab reads
the enriched Phase 5 `/licenses/` report; the SBOM tab reads the license parsed back out of the
**stored SBOM document**, which the generator never populated. Story 8.6 flagged this exactly as
a known caveat ("the current SBOM generator does not embed per-component licenses … kept for when
generation is enriched"). This story is that enrichment.

### The design decision (Phase 3 vs Phase 5 ordering) — DECIDED

**Resolve each package's license at Phase 3 generation time using the same normalization Phase 5
uses, and write it into the SBOM there. Do not rewrite the persisted blob downstream.**

Investigation of the ordering concern (AD-6, memory `phase3-writes-blob-not-phase8`):

- Phase 3 (`generate_sbom_document`) **already writes the SBOM blob** to `result_key`
  (`tasks/sbom_pipeline.py:167`); the chord of analysis phases (incl. Phase 5 license) runs
  **after** it; Phase 8 (`persist_artifacts`, `sbom_pipeline.py:197-208`) only finalizes the DB.
  So the license must be present **when Phase 3 writes the blob** — enriching Phase 3's output is
  the only AD-6-preserving option. Phase 8 rewriting the blob is explicitly **rejected** (would
  violate AD-6; flag loudly if ever proposed).
- **The license is not fundamentally a "Phase 5-only" datum.** Phase 5's license comes from the
  **PyPI JSON API** via `_extract_license` (`analysis/services/license.py:71-90`), which is
  equally reachable at Phase 3. Resolution (Story 3.3, `sbom/parsers/*`) fetches **no** license
  today, and `PackageSpec` (`sbom/parsers/_types.py:21-31`) carries no license field — so the
  data isn't already threaded, but it is cheap to resolve at generation time.
- **No doubled external load.** `http.pypi_session()` is a 1h-cached, 5 req/s
  `CachedLimiterSession` (`analysis/services/http.py:84-89`). Phase 3 resolving the license map
  warms the cache; Phase 5's `classify` fetch for the same `(name, version)` hits the cache — the
  external PyPI call happens once, not twice.
- **Single source of truth (AC #4).** Both the SBOM component license and the Licenses tab derive
  from the **same** `_extract_license` normalization (PEP 639 → classifier→SPDX → free-text), so
  they cannot diverge.

**Alternative considered and rejected:** capture the license at resolution (Phase 1/2) onto a new
`PackageSpec.license` field and thread it through the Celery chain (the `tag_relationships` /
`tag_ecosystems` pattern from Stories 8.3/8.8). Rejected: resolution fetches no PyPI metadata
today, so this adds N fetches to Phase 1/2 **and** enlarges the threaded payload, for no benefit
over resolving in Phase 3 — where the blob is written anyway. It remains a viable future shape if
resolution ever starts fetching PyPI metadata for another reason.

**Purity note (keep the Story 3.4 contract):** `generation.generate_sbom_document` is deliberately
I/O-free and independently testable. Keep it that way — do the PyPI resolution in the **task**
(`tasks/sbom_pipeline.py`) and pass a `license_map` into the pure serializer as a parameter, so
the AC #6 unit test drives it with a fixture map and no network.

### CycloneDX license representation

Use `cyclonedx-python-lib` (11.11.0, CycloneDX 1.6) `LicenseFactory().make_from_string(value)`
(`cyclonedx.factory.license`): a known SPDX id → `SpdxLicense`, an SPDX expression (e.g.
`Apache-2.0 OR MIT`) → `LicenseExpression`, any other non-empty string → a named
`DisjunctiveLicense`/`License`. Add it to `component.licenses`. For `None`/empty, add nothing —
that yields `licenses: []`, which `document.py::_cyclonedx_license` maps back to `None` → `—`
(AC #2). The generator sets no `purl` on CycloneDX components today (only name/version/type/
bom_ref + a `sbom:relationship` property, `generation.py:97-106`) — leave that unchanged.

### SPDX license representation

`lib4sbom` (0.10.4) `SBOMPackage`: `set_licenseconcluded(value)` + `set_licensedeclared(value)`;
`NOASSERTION` for unknown. `document.py::_spdx_license` (`:361-367`) reads
`licenseConcluded`/`licenseDeclared`, so this is what the viewer surfaces for SPDX output.

### Viewer path (no change expected)

`sbom/document.py::normalize_components` already extracts license back out of all three formats
(`_component` `:203-218`; `_cyclonedx_license` `:248-263`; `_cyclonedx_xml_licenses` `:313-320`;
`_spdx_license` `:361-367`) and the endpoint returns it as `SbomComponent.license`
(`frontend/src/api/sbom.ts:6-13`). `SbomTab.tsx:153` renders `row.license ?? '—'`. So once
generation writes the license, the Components table and Raw view populate with no viewer change —
the only frontend work is the null → `—` test assertion (Task 5).

### Project Structure Notes

- Backend generation: `backend/generate_sbom/sbom/generation.py` (CycloneDX `:97-106`, SPDX
  `:160-172`); Phase 3 task `backend/generate_sbom/tasks/sbom_pipeline.py:144-176` (blob write
  `:167`); shared normalizer from `backend/generate_sbom/analysis/services/license.py:71-90`
  (+ `_CLASSIFIER_SPDX` `:50-68`); cached session `analysis/services/http.py:84-89`.
- Viewer (read-only for this story): `backend/generate_sbom/sbom/document.py`,
  `frontend/src/components/SbomTab.tsx`, `frontend/src/api/sbom.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.25: Include License in the SBOM Document]
- SBOM generation: `backend/generate_sbom/sbom/generation.py:56-119` (CycloneDX), `:137-183` (SPDX)
- Phase 3 task + blob write: `backend/generate_sbom/tasks/sbom_pipeline.py:144-176` (save `:167`), chain `:88-102`
- License normalization (single source): `backend/generate_sbom/analysis/services/license.py:71-90`, `:50-68`, `:111-125`
- Cached PyPI session: `backend/generate_sbom/analysis/services/http.py:84-89`
- Viewer parse-back: `backend/generate_sbom/sbom/document.py:203-218,248-263,313-320,361-367`
- Viewer UI: `frontend/src/components/SbomTab.tsx:143,153`; type `frontend/src/api/sbom.ts:6-13`; test `frontend/src/components/SbomTab.test.tsx`
- `PackageSpec` (no license field): `backend/generate_sbom/sbom/parsers/_types.py:21-31`
- AD-6 / phase split: memory `phase3-writes-blob-not-phase8`; Story 3.4 completion notes (blob written in Phase 3, Phase 8 finalizes DB)
- Related stories: `8-6-in-app-sbom-viewer-tab.md` (the caveat this resolves), `4-3-license-compliance-report-phase-5.md` (the shared normalization), `5-4-licenses-tab.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
