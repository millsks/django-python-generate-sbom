# Story 8.2: [Spike] Direct vs Transitive Dependency Design

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the team,
I want a short design decision on how to capture and represent direct-vs-transitive dependencies,
so that the implementation stories (8.3–8.5) build on one agreed mechanism instead of guessing.

This is a **time-boxed spike** (target: half a day). The deliverable is a design note, not
production code. Small throwaway proofs-of-concept are encouraged to de-risk the decision.

## Acceptance Criteria

1. Given each supported manifest format (`requirements.txt`, `pyproject.toml`, `pixi.toml`, `pixi.lock`, `conda environment.yml`), when the spike completes, then the design note documents how the *direct* (declared) set is identified for that format, and the confidence/limitations of each approach.
2. Given the resolved data model, when the spike completes, then the note specifies how `PackageSpec` (and the threaded pipeline payload) carries the relationship without breaking the chain contract (AD-6: keys/counts, not blobs).
3. Given the two SBOM standards in scope (CycloneDX, SPDX), when the spike completes, then the note documents the native representation of the direct/transitive relationship in each and what our serializers must emit to remain schema-valid.
4. Given a format where the direct set cannot be reliably determined, when the spike completes, then the note states the agreed fallback behavior (e.g. mark all transitive/unknown) rather than leaving it open.
5. Given the spike's conclusions, when it is written up, then it lands as a short design note (a candidate architecture decision) under the planning artifacts and is explicitly cited by Stories 8.3–8.5, which are only then contexted into full story files and moved from `backlog` to `ready-for-dev`.

## Tasks / Subtasks

- [ ] Task 1 — Per-format direct-set identification (AC: #1)
  - [ ] `requirements.txt`: the parsed declared lines (pre-`uv pip compile`) are the direct set; confirm `uv pip compile` annotations (`# via -r requirements.in` vs `# via <pkg>`) can classify the compiled output, and whether `--no-annotate` should be dropped
  - [ ] `pyproject.toml`: `[project.dependencies]` (+ optional-dependencies groups?) as the direct set; how it maps onto the compiled tree
  - [ ] `pixi.toml`: declared `[dependencies]`/`[pypi-dependencies]` vs the compiled/solved set
  - [ ] `pixi.lock`: does the lock encode top-level requests vs. the full solved environment? Determine if direct is recoverable
  - [ ] `conda environment.yml`: declared `dependencies:` vs. the solver's full set
- [ ] Task 2 — Data model & pipeline threading (AC: #2)
  - [ ] Decide the `PackageSpec` field shape (`direct: bool` vs `relationship: Literal["direct","transitive","unknown"]`)
  - [ ] Confirm it serializes cleanly through the existing `asdict`/`PackageSpec(**spec)` chain hops (AD-6) and note any migration to stored job data
- [ ] Task 3 — SBOM standard representation (AC: #3)
  - [ ] CycloneDX: `dependencies` graph and/or component `scope`; what `cyclonedx-python-lib` supports for JSON + XML
  - [ ] SPDX: relationship types (`DESCRIBES`/`DEPENDS_ON`) via `lib4sbom`; what's emittable
  - [ ] Note schema-validity constraints for each
- [ ] Task 4 — Fallback & edge cases (AC: #4)
  - [ ] Agree behavior when direct cannot be determined; how the graph/viewer should render "unknown"
- [ ] Task 5 — Write-up (AC: #5)
  - [ ] Produce the design note under `_bmad-output/planning-artifacts/` (research or architecture), phrased as a candidate AD
  - [ ] Update 8.3–8.5 to cite it; flip their sprint-status entries to `ready-for-dev` once contexted

## Dev Notes

### Why a spike

Today resolution is **flat**: `requirements.py` parses the declared lines then hands them to `uv pip compile`, whose output (`parse_compiled`) strips the `# via` annotations that carry provenance. So the direct set exists momentarily and is discarded. Each format identifies "direct" differently, and each SBOM standard encodes the relationship differently — enough branching that guessing per-story would risk rework. This spike fixes the mechanism once. [Source: backend/generate_sbom/sbom/parsers/requirements.py, backend/generate_sbom/sbom/parsers/_uv.py]

### Known starting points

- `uv pip compile` emits `# via -r requirements.in` for roots and `# via <parent>` for transitive deps; re-enabling annotations (currently `--no-header --quiet`) is the likely lever for the requirements/pyproject/pixi.toml paths.
- `pixi.lock` and `conda environment.yml` are solved trees; whether the *declared* top-level survives into the lock/solve output needs verification (Task 1).
- `PackageSpec` is a frozen dataclass threaded as `asdict(...)` dicts through the Celery chain (AD-6) — adding a field is cheap but must be handled at every `PackageSpec(**spec)` reconstruction.

### Deliverable

A concise decision note (not code) that 8.3 (capture), 8.4 (SBOM encoding), and 8.5 (graph viz) cite. It should read like a candidate architecture decision so it can be folded into the spine. Keep proofs-of-concept out of the mainline (throwaway branch or scratch).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.2]
- [Source: backend/generate_sbom/sbom/parsers/_uv.py]
- [Source: backend/generate_sbom/sbom/parsers/_types.py — PackageSpec]
- [Source: prd.md#FR-4.3, FR-4.4]
- [Source: ARCHITECTURE-SPINE.md#AD-6 — keys/counts through the chain]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
