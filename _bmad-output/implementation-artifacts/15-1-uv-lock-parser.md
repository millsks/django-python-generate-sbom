# Story 15.1: uv.lock Parser

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement this story **first** in Epic 15. It establishes the shared lockfile-reader conventions
> (and any small `sbom/parsers/_lockfile.py` helper) that Stories 15.2 (`poetry.lock`) and 15.3
> (`Pipfile.lock`) reuse.

## Story

As a user,
I want to upload a `uv.lock` file,
so that I get an SBOM built from its exact pinned closure without the app re-resolving anything.

## Acceptance Criteria

1. **Detection.** A file named `uv.lock` is detected as a new `ManifestUpload.Format.UV_LOCK` via an
   exact-match filename pattern in `manifests/detection.py`; `validate_parseable` safe-parses it as TOML
   (`tomllib`); and the `SUPPORTED` string lists `uv.lock`.
2. **Direct-read parser (skip resolution).** A new `sbom/parsers/uv_lock.py` `resolve(content) -> list[PackageSpec]`
   reads every top-level `[[package]]` table into a pinned `PackageSpec` (name + exact `version`, PyPI
   ecosystem) **with no re-resolution** — no `uv pip compile`, no subprocess, no network — mirroring
   `pixi_lock.resolve`. It is registered in `sbom/parsers/__init__.py` `_RESOLVERS` under `UV_LOCK`.
3. **Direct vs transitive.** The root project entry — the `[[package]]` whose `source` is `editable`/`virtual`
   (`"."`) — supplies the declared set from its `dependencies` (plus its optional-dependency and
   dev-dependency groups). `tag_relationships` marks those `direct` and the rest `transitive`. If no root
   package can be identified, every package falls back to `unknown` (the `pixi.lock` precedent). The
   root/virtual project entry itself is **excluded** from the emitted component list.
4. **Enum + migration + wiring.** `ManifestUpload.Format` gains `UV_LOCK = "uv_lock", "uv.lock"`; a Django
   migration for the `manifests` app is generated (choice-only `AlterField`; `detected_format` `max_length=20`
   already fits `uv_lock`). `estimate_seconds` gains a `UV_LOCK` entry reflecting the skipped resolution step.
5. **Frontend + prose.** `frontend/src/api/manifestFormats.ts` `MANIFEST_FORMATS` gains `'uv_lock'` in enum
   order; the upload copy (`frontend/src/pages/HomePage.tsx`) and the supported-format prose/count
   (`one-pager.md`, `docs/how-to/generate-sbom.md`, `docs/index.md`) are updated to include `uv.lock`. The
   Story 6.4 consistency test (`test_manifest_format_consistency.py`) stays green.
6. **Tests + gate.** `pixi run ci` is green (backend coverage ≥90%) with: a parser unit test against a
   committed real `uv.lock` fixture (self-contained, no network) asserting the pinned set + direct/transitive
   tags; a detection test for `uv.lock`; and the manifest-format consistency test kept passing.

## Tasks / Subtasks

- [ ] **Task 1 — Detection (AC: #1)**
  - [ ] `manifests/detection.py`: add `(re.compile(r"^uv\.lock$"), _Format.UV_LOCK)` to `_FORMAT_PATTERNS`
        (filename is lowercased before match). Append `uv.lock` to `SUPPORTED`.
  - [ ] Extend `validate_parseable` so `UV_LOCK` is safe-parsed via `tomllib.loads` (group it with the TOML
        branch alongside `PYPROJECT`/`PIXI_TOML`).
- [ ] **Task 2 — Enum + migration (AC: #4)**
  - [ ] `manifests/models.py`: add `UV_LOCK = "uv_lock", "uv.lock"` to `ManifestUpload.Format`.
  - [ ] `pixi run` `makemigrations manifests` → commit the generated migration (no `max_length` change).
- [ ] **Task 3 — Parser (AC: #2, #3)**
  - [ ] New `sbom/parsers/uv_lock.py`: `tomllib.loads` the content; on failure raise `ResolutionError`; on a
        non-dict / missing `package` array raise `ResolutionError` (mirror `pixi_lock`'s guards).
  - [ ] Emit one `PackageSpec` per `[[package]]` with `name`, `str(version)`, `ecosystem=PYPI`; skip the
        root/virtual project entry.
  - [ ] Build the declared set from the root entry's `dependencies` (+ `optional-dependencies` /
        `dev-dependencies` group tables) and apply `tag_relationships`; fall back to leaving `unknown` when no
        root entry is found.
  - [ ] Optionally introduce `sbom/parsers/_lockfile.py` for the pieces 15.2/15.3 will share (e.g. a
        `pypi_spec(name, version)` builder, a non-dict guard). Keep it minimal — the three lock schemas differ.
  - [ ] Register `UV_LOCK: uv_lock.resolve` in `sbom/parsers/__init__.py` `_RESOLVERS`.
- [ ] **Task 4 — Estimate + frontend + prose (AC: #4, #5)**
  - [ ] `sbom/services.py` `estimate_seconds`: add a `UV_LOCK` branch (lockfile → no resolution; a lower
        estimate than the resolving formats).
  - [ ] `frontend/src/api/manifestFormats.ts`: add `'uv_lock'` in the same order as the backend enum.
  - [ ] `frontend/src/pages/HomePage.tsx`: update the upload-format blurb to mention lockfiles.
  - [ ] Update the supported-format list/count in `one-pager.md`, `docs/how-to/generate-sbom.md`,
        `docs/index.md`.
- [ ] **Task 5 — Tests (AC: #6)**
  - [ ] Commit a small but real `uv.lock` fixture (a couple of direct deps with a transitive tail). Add a
        parser test asserting exact pins + `direct`/`transitive` tags and that no re-resolution occurs (no
        `uv` subprocess).
  - [ ] Add a detection test for `uv.lock`.
  - [ ] Confirm `test_manifest_format_consistency.py` passes with the new format in both lists.
  - [ ] `pixi run ci` green.

## Dev Notes

### The skip-resolution precedent (reuse this) — verified

The Celery pipeline **always** runs Phase 2 and needs **no change**:
`tasks/sbom_pipeline.py::resolve_transitive_deps` → `sbom/services.py::resolve_job_packages` (reads the
uploaded bytes) → `sbom/parsers/__init__.py::resolve_packages(format, content)` → the format's `resolve`.
For lockfiles the short-circuit lives entirely **inside the resolver**: `pixi_lock.resolve`
(`sbom/parsers/pixi_lock.py`) reads the fully-solved set straight from the file — no `uv_pip_compile`, no
subprocess, no network. `uv.lock` follows the same shape; there is nothing to add to the pipeline or services
beyond the `_RESOLVERS` registration.

`_uv.py` is **not** reused: `sbom/parsers/_uv.py::uv_pip_compile` is the *resolution* helper for loose
requirements (`pyproject.py`, `pixi_toml.py`, `requirements.py`). `uv.lock` is already resolved and must be
read directly, so this story adds a **new** pure-`tomllib` reader.

### PackageSpec contract — verified

`sbom/parsers/_types.py`: `PackageSpec(name, version, extras=(), markers="", relationship="unknown",
ecosystem="pypi")`. Helpers: `tag_relationships(specs, declared_names)` marks specs `direct` when the
PEP 503-canonical name is in the declared set else `transitive`; `mark_ecosystem(specs, ecosystem)` sets a
uniform ecosystem. Default `ecosystem` is already `pypi`, so no ecosystem tagging is needed for a PyPI-only
lockfile. `pixi_lock.resolve` leaves `relationship` at the `unknown` default; `test_pixi_lock_packages_are_unknown`
pins that behavior — the `unknown` fallback here is the same precedent.

### uv.lock schema (verify against the committed fixture)

TOML. Top-level `version` / `requires-python`; an array of `[[package]]` tables, each with `name`, `version`,
`source` (an inline table: `{ registry = "https://pypi.org/simple" }` for PyPI deps, or `{ editable = "." }` /
`{ virtual = "." }` for the project root). Per-package `dependencies = [{ name = "..." }, ...]` edges;
optional groups under `[package.optional-dependencies]` and `[package.dev-dependencies]`. Hashes live under
`[[package.wheels]]` and `[package.sdist]` (`hash = "sha256:..."`) — capture them only if a downstream field
exists for them; otherwise the exact pin + ecosystem is the load-bearing output (matching `pixi_lock`).

**Direct set:** the root `[[package]]` (source `editable`/`virtual` = `"."`) lists the project's own
`dependencies` — those are the direct deps. This is a real advantage over `pixi.lock`, so uv.lock *can* split
direct/transitive; do so via `tag_relationships` and exclude the root entry from components.

### Detection specifics — verified

`manifests/detection.py::detect_format` lowercases the filename then `re.search`es `_FORMAT_PATTERNS` in
order; distinct tokens mean no collision with the existing `pixi*.lock` pattern. Use an anchored exact pattern
`^uv\.lock$` (the new lockfiles have fixed names — the task calls for exact-match, not the prefix/suffix
tolerance the older manifests use). `validate_parseable` currently branches TOML (`tomllib`) vs YAML
(`yaml.safe_load`); add `UV_LOCK` to the TOML branch.

### estimate_seconds — verified

`sbom/services.py::estimate_seconds(detected_format, size_bytes)` = `15 + MB*10`, `+10` for `CONDA`. A
lockfile skips Phase 2 resolution, so give `UV_LOCK` a lower estimate (e.g. subtract the resolution overhead)
to keep the ETA truthful. Not load-bearing; keep it simple.

### Frontend consistency (Story 6.4) — verified

`backend/tests/unit/test_manifest_format_consistency.py` asserts the ordered `MANIFEST_FORMATS` array in
`frontend/src/api/manifestFormats.ts` equals `list(ManifestUpload.Format.values)`. Add `'uv_lock'` at the
matching position or the test fails. HomePage upload copy is at `frontend/src/pages/HomePage.tsx:35`
(`'requirements.txt, pyproject.toml, or environment.yml.'`).

### Prose/count touch-points

`_bmad-output/planning-artifacts/architecture/.../one-pager.md` says "5 Python package formats";
`docs/how-to/generate-sbom.md` and `docs/index.md` enumerate the formats. Add `uv.lock`. (The count reaches 8
once all three Epic 15 stories land — 15.3 flips the total.)

### Project Structure Notes

- Parser is a pure function (AD-3): bytes in, `list[PackageSpec]` out. No I/O in the parser.
- Existing parser tests (`backend/tests/unit/test_parsers.py`) drive resolvers via
  `resolve_packages("<format>", content)`; follow that entry point. A committed fixture file is requested for
  this story (self-contained, no network), read via `Path(__file__).parent / "fixtures" / "uv.lock"` or
  equivalent; the existing tests use inline byte strings, either is acceptable so long as the fixture is real.

### References

- `backend/generate_sbom/manifests/models.py` — `ManifestUpload.Format`.
- `backend/generate_sbom/manifests/detection.py` — `_FORMAT_PATTERNS`, `SUPPORTED`, `validate_parseable`.
- `backend/generate_sbom/sbom/parsers/pixi_lock.py` — the lockfile direct-read precedent.
- `backend/generate_sbom/sbom/parsers/_types.py` — `PackageSpec`, `tag_relationships`, `mark_ecosystem`.
- `backend/generate_sbom/sbom/parsers/__init__.py` — `_RESOLVERS` dispatch.
- `backend/generate_sbom/sbom/parsers/_uv.py` — the `uv pip compile` resolver (NOT reused here).
- `backend/generate_sbom/tasks/sbom_pipeline.py` — Phase 2 `resolve_transitive_deps` (unchanged).
- `backend/generate_sbom/sbom/services.py` — `resolve_job_packages`, `estimate_seconds`.
- `frontend/src/api/manifestFormats.ts`, `frontend/src/pages/HomePage.tsx`.
- `backend/tests/unit/test_manifest_format_consistency.py`, `backend/tests/unit/test_parsers.py`.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
