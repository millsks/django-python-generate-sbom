# Story 3.3: Manifest Parsers & Transitive Resolution (Phases 1–2)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the SBOM pipeline,
I want to parse each supported manifest format and resolve its full transitive dependency tree,
so that a complete resolved package list is available for SBOM generation.

## Acceptance Criteria

1. Given a `pixi.lock` file, when Phase 2 runs, then it is parsed with PyYAML safe load (not `tomllib`) and the full transitive tree is read directly from the lock file with no external resolver invoked (FR-4.3).
2. Given a `pixi.toml`, `pyproject.toml` (no lock), or `requirements.txt`, when Phase 2 runs, then the manifest is parsed with the correct loader (`tomllib` / `packaging.requirements.Requirement`) and `uv pip compile` is invoked as a subprocess to resolve the transitive tree (FR-4.3).
3. Given a `conda environment.yml`, when Phase 2 runs, then it is parsed with PyYAML safe load and the `conda`/`mamba` solver is invoked; if the solver binary is unavailable the phase fails with a descriptive error naming the missing solver (FR-4.3).
4. Given each parser lives in `sbom/parsers/`, when a parser is implemented, then it is a pure service-layer function taking plain inputs and returning a resolved package list (name, version, dependencies) — no `HttpRequest`, `Response`, or Celery `Task` coupling (AD-3).
5. Given Phase 1 (detect & parse) and Phase 2 (resolve), when each phase starts, then `task.update_state(state='PROGRESS', meta={'progress': N, 'current_step': '<phase name>'})` is called with thresholds in the 0–15% (Phase 1) and 15–40% (Phase 2) ranges (FR-4.2).
6. Given each pipeline phase, when it starts and completes, then a structured `structlog` entry is emitted with phase name, duration, and package count, binding `org_id` and `task_id` (NFR-6.1).
7. Given unit tests with representative fixture files for all five formats, when `pixi run cov` runs, then each parser is exercised and coverage on `sbom/parsers/` is ≥90%.

## Tasks / Subtasks

- [ ] Task 1 — Parser interface (AC: #4)
  - [ ] Define the common parser contract `parse(content: bytes) -> list[PackageSpec]` where `PackageSpec` = `{name, version, extras, markers}` (solution-design §3.3)
  - [ ] Parsers are pure service functions — no request/response/task coupling (AD-3)
- [ ] Task 2 — Lock-file parser: `pixi_lock.py` (AC: #1)
  - [ ] Parse `pixi.lock` with PyYAML `safe_load` (it is YAML despite `.lock`) — NEVER `tomllib`
  - [ ] Read the full resolved set directly; no resolver subprocess
- [ ] Task 3 — Manifest-only parsers with `uv pip compile` (AC: #2)
  - [ ] `requirements.py` — parse with `packaging.requirements.Requirement`, then `uv pip compile` subprocess for transitive closure
  - [ ] `pyproject.py` — parse with `tomllib`; `uv pip compile` when no lock present
  - [ ] `pixi_toml.py` — parse TOML; `uv pip compile` subprocess
  - [ ] Subprocess receives file PATHS, never unsanitized content as shell args (NFR-3.1 / security design)
- [ ] Task 4 — conda parser: `conda.py` (AC: #3)
  - [ ] Parse `environment.yml` with PyYAML `safe_load`; invoke `conda`/`mamba` solver (`conda env export` path per solution-design §3.3)
  - [ ] If solver binary absent → fail the phase with a descriptive error naming the missing solver (conda/mamba is a REQUIRED runtime dep)
- [ ] Task 5 — Phase 1 & 2 task bodies (AC: #5, #6)
  - [ ] `detect_and_parse_manifest` (Phase 1, `pipeline` queue): download manifest from S3, detect format, dispatch to the right parser; progress 0→15%
  - [ ] `resolve_transitive_deps` (Phase 2, `pipeline` queue): produce the full package list; progress 15→40%
  - [ ] Both call `task.update_state(...)` at phase start (AC #5) and emit start/complete structlog with phase name, duration, package count, binding `org_id`+`task_id` (AC #6)
- [ ] Task 6 — Tests (AC: #7)
  - [ ] Unit fixtures for all five formats; assert resolved package list shape
  - [ ] Unit: pixi.lock parsed as YAML (a TOML parse would fail — assert it does not regress)
  - [ ] Unit: missing conda solver → descriptive error
  - [ ] Mock `uv pip compile` subprocess in unit tests; a real invocation belongs in integration
  - [ ] ≥90% coverage on `sbom/parsers/`; `pixi run ci` exits 0

## Dev Notes

### Parser contract (solution-design.md §3.3)

```python
def parse(content: bytes) -> list[PackageSpec]:
    """Returns [{name, version, extras, markers}, ...]"""
```

Resolution strategy by format:
- Lock file (`pixi.lock`) → read full resolved set directly, no resolver.
- Manifest-only (`pyproject.toml`, `requirements.txt`, `pixi.toml`) → `uv pip compile` subprocess for transitive closure.
- conda (`environment.yml`) → invoke `conda`/`mamba` solver (`conda env export`).

### CRITICAL specifics

- `pixi.lock` is **YAML** — parse with PyYAML `safe_load`, NOT `tomllib` (addendum + FR-4.3). Getting this wrong is a known footgun.
- conda/mamba is a **required runtime dependency**; absence → descriptive failure, not silent skip.
- Subprocess calls (`uv pip compile`, `conda`) receive file paths only — never file content as shell args (security design).
- Safe loaders only (`tomllib`, PyYAML `safe_load`, `packaging`) — no `eval`/`exec`.

### Phase mapping (solution-design.md §4.2; AD-4)

| Phase | Queue | Progress | Work |
|---|---|---|---|
| 1 detect & parse | `pipeline` | 0→15% | download manifest, detect format, call parser |
| 2 resolve transitive | `pipeline` | 15→40% | `uv pip compile` or lock read → full package list |

Progress via `task.update_state(state='PROGRESS', meta={'progress': N, 'current_step': '<phase name>'})`. All tasks `@shared_task` (no Celery app import). Structured start/complete logs (NFR-6.1): phase name, duration, package count, bound `org_id`+`task_id`.

### Service purity (AD-3)

Parsers and resolution are pure service functions callable from both a Celery task and (hypothetically) a view without modification — plain inputs/outputs, no framework objects.

### Project Structure Notes

- `<project_slug>/sbom/parsers/`: `requirements.py`, `pyproject.py`, `pixi_lock.py`, `pixi_toml.py`, `conda.py`.
- Phase 1/2 task bodies live in `<project_slug>/tasks/sbom_pipeline.py`; the chain wiring is Story 3.5. This story delivers the parsers + the two phase functions; 3.5 assembles them into the chain with Phase 3/8 and the analysis-group stub.
- Depends on Story 3.1 (`ManifestUpload`, storage) and Story 1.3 (Celery app, structlog). Does not depend on Epic 4.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3: Manifest Parsers & Transitive Resolution (Phases 1–2)]
- [Source: solution-design.md#3.3 sbom/ — Parsers]
- [Source: solution-design.md#4.2 Phase breakdown]
- [Source: PRD addendum.md#Manifest Parser Implementation Notes]
- [Source: ARCHITECTURE-SPINE.md#AD-3 — Service layer purity]
- [Source: ARCHITECTURE-SPINE.md#AD-4 — Two Celery queues]
- [Source: prd.md#FR-4.2, FR-4.3, NFR-6.1]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
