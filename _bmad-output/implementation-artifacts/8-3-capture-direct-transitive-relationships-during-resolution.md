# Story 8.3: Capture Direct/Transitive Relationships During Resolution

Status: ready-for-dev

<!-- Contexted from the 8.2 spike: planning-artifacts/research/direct-vs-transitive-design.md -->

## Story

As a user,
I want the pipeline to know which packages I declared vs. which were pulled in transitively,
so that the SBOM document, graph, and viewer can show the distinction.

## Acceptance Criteria

1. Given the resolved `PackageSpec`, when a manifest is resolved, then each spec carries a `relationship` field with value `direct`, `transitive`, or `unknown` (default `unknown`).
2. Given `requirements.txt`, `pyproject.toml`, and `pixi.toml`, when resolved, then packages whose canonical name (PEP 503) is in the manifest's declared dependency set are tagged `direct` and the rest `transitive`.
3. Given `conda environment.yml`, when resolved, then packages matching the declared `dependencies:` (including nested `pip:` entries, version specifiers stripped) are tagged `direct`, the rest `transitive`.
4. Given `pixi.lock` (a full solved environment with no declared/requested marker), when resolved, then every package is tagged `unknown` — never a guessed direct/transitive split.
5. Given a package that is both declared and pulled in transitively, when tagged, then it is `direct` (declared wins).
6. Given the resolved list threads through the Celery chain, when it is passed between phases, then `relationship` travels with it within the existing `asdict`/`PackageSpec(**spec)` contract (AD-6) and is covered by tests.

## Tasks / Subtasks

- [ ] Task 1 — Model field (AC: #1, #6)
  - [ ] Add `relationship: str = "unknown"` to `PackageSpec` (`parsers/_types.py`); confirm `asdict`/`PackageSpec(**spec)` round-trips through `resolve_transitive_deps` → `generate_sbom_document`
  - [ ] Add module constants `DIRECT = "direct"`, `TRANSITIVE = "transitive"`, `UNKNOWN = "unknown"`
- [ ] Task 2 — Shared tagging helper (AC: #2, #3, #5)
  - [ ] Add `tag_relationships(specs, declared_names)` in the parsers package: canonicalize both sides (`packaging.utils.canonicalize_name`), return specs with `relationship` set (`direct` if in declared set else `transitive`)
- [ ] Task 3 — Wire each resolver (AC: #2, #3, #4, #5)
  - [ ] `requirements.py`: collect declared `Requirement(line).name`s; tag the compiled result
  - [ ] `pyproject.py`: declared names from `[project.dependencies]` / Poetry deps; tag
  - [ ] `pixi_toml.py`: declared names from `[dependencies]` + `[pypi-dependencies]`; tag
  - [ ] `conda.py`: declared names from `dependencies:` (+ nested `pip:`), specifiers stripped; tag the solver output
  - [ ] `pixi_lock.py`: tag every spec `unknown` (no declared set available)
- [ ] Task 4 — Tests
  - [ ] Unit per resolver: direct vs transitive tagging for a representative manifest; declared-wins case; `pixi.lock` → all `unknown`
  - [ ] Unit: `relationship` survives the chain hop (`asdict` → `PackageSpec(**spec)`)
  - [ ] `pixi run ci` exits 0 with ≥90% coverage on the new code

## Dev Notes

### Mechanism (from the 8.2 spike)

Declared-set intersection by canonicalized name — the declared set is already parsed
in every resolver except `pixi.lock`; keep the intersection logic in the shared
`tag_relationships` helper. Do **not** change the `uv`/`conda` invocations for this
story (annotation-based edge extraction is a deferred enhancement). [Source:
planning-artifacts/research/direct-vs-transitive-design.md#Decision 1]

### Model & chain (from the 8.2 spike)

`relationship: str = "unknown"` on the frozen `PackageSpec`; the default keeps the
single `asdict` → `PackageSpec(**spec)` chain hop backward-compatible. Packages are
transient (never persisted), so there is no stored-data migration. [Source:
research/direct-vs-transitive-design.md#Decision 2; sbom_pipeline.py resolve→generate]

### Fallback (from the 8.2 spike)

Unmatched packages and all of `pixi.lock` → `unknown`, never guessed. [Source:
research/direct-vs-transitive-design.md#Decision 4]

### References

- [Source: _bmad-output/planning-artifacts/research/direct-vs-transitive-design.md]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.3]
- [Source: backend/generate_sbom/sbom/parsers/ — all resolvers]
- [Source: backend/generate_sbom/tasks/sbom_pipeline.py — chain hop]
- [Source: ARCHITECTURE-SPINE.md#AD-6]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
