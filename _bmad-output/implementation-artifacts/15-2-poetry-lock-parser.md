# Story 15.2: poetry.lock Parser

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement after **Story 15.1 (`uv.lock`)**, which establishes the shared lockfile-reader
> conventions (and any `sbom/parsers/_lockfile.py` helper) this story reuses.

## Story

As a user,
I want to upload a `poetry.lock` file,
so that I get an SBOM built from its exact pinned closure without the app re-resolving anything.

## Acceptance Criteria

1. **Detection.** A file named `poetry.lock` is detected as a new `ManifestUpload.Format.POETRY_LOCK` via an
   exact-match filename pattern in `manifests/detection.py`; `validate_parseable` safe-parses it as TOML
   (`tomllib`); and the `SUPPORTED` string lists `poetry.lock`.
2. **Direct-read parser (skip resolution).** A new `sbom/parsers/poetry_lock.py`
   `resolve(content) -> list[PackageSpec]` reads every top-level `[[package]]` table into a pinned
   `PackageSpec` (name + exact `version`, PyPI ecosystem) **with no re-resolution** — no subprocess, no
   network — mirroring `pixi_lock.resolve` and reusing the 15.1 conventions. It is registered in
   `sbom/parsers/__init__.py` `_RESOLVERS` under `POETRY_LOCK`.
3. **Direct vs transitive — all `unknown` (justified).** `poetry.lock` alone does **not** declare the direct
   set; the direct dependencies live in the sibling `pyproject.toml` `[tool.poetry.dependencies]`, which is
   not part of the lock. Therefore every package is recorded as resolved with relationship `unknown` (the
   `pixi.lock` precedent — never guess a declared set). This decision is documented in the parser docstring.
   The package group (`main`/`dev`, from `groups` in newer Poetry or `category` in older) is read tolerantly
   but is **not** treated as a direct/transitive signal.
4. **Enum + migration + wiring.** `ManifestUpload.Format` gains `POETRY_LOCK = "poetry_lock", "poetry.lock"`;
   a Django `manifests` migration is generated (choice-only `AlterField`; `poetry_lock` fits
   `max_length=20`). `estimate_seconds` gains a `POETRY_LOCK` entry reflecting the skipped resolution step.
5. **Frontend + prose.** `frontend/src/api/manifestFormats.ts` `MANIFEST_FORMATS` gains `'poetry_lock'` in
   enum order; the upload copy (`frontend/src/pages/HomePage.tsx`) and the supported-format prose/count
   (`one-pager.md`, `docs/how-to/generate-sbom.md`, `docs/index.md`) are updated to include `poetry.lock`. The
   Story 6.4 consistency test stays green.
6. **Tests + gate.** `pixi run ci` is green (backend coverage ≥90%) with: a parser unit test against a
   committed real `poetry.lock` fixture covering **both** an older `category` + `[metadata.files]` shape and a
   newer `groups` + `[[package.files]]` shape (self-contained, no network); a detection test for
   `poetry.lock`; and the manifest-format consistency test kept passing.

## Tasks / Subtasks

- [ ] **Task 1 — Detection (AC: #1)**
  - [ ] `manifests/detection.py`: add `(re.compile(r"^poetry\.lock$"), _Format.POETRY_LOCK)` to
        `_FORMAT_PATTERNS`; append `poetry.lock` to `SUPPORTED`; add `POETRY_LOCK` to the TOML branch of
        `validate_parseable`.
- [ ] **Task 2 — Enum + migration (AC: #4)**
  - [ ] `manifests/models.py`: add `POETRY_LOCK = "poetry_lock", "poetry.lock"`.
  - [ ] `pixi run` `makemigrations manifests` → commit the migration.
- [ ] **Task 3 — Parser (AC: #2, #3)**
  - [ ] New `sbom/parsers/poetry_lock.py`: `tomllib.loads`; guard bad-TOML / non-dict / missing `package`
        array with `ResolutionError` (mirror `pixi_lock`).
  - [ ] Emit one `PackageSpec` per `[[package]]` (`name`, `str(version)`, `ecosystem=PYPI`); leave
        `relationship` at the `unknown` default.
  - [ ] Read the group (`groups` list or legacy `category` string) tolerantly; do not use it for
        direct/transitive. (Optionally carry it forward only if a downstream field exists — otherwise ignore.)
  - [ ] Reuse the 15.1 `_lockfile.py` helper(s) where applicable. Register `POETRY_LOCK: poetry_lock.resolve`
        in `_RESOLVERS`.
- [ ] **Task 4 — Estimate + frontend + prose (AC: #4, #5)**
  - [ ] `estimate_seconds`: add a `POETRY_LOCK` branch (lockfile → no resolution).
  - [ ] `manifestFormats.ts`: add `'poetry_lock'` in enum order; update `HomePage.tsx` copy and the
        supported-format prose/count in the one-pager + docs how-to/index.
- [ ] **Task 5 — Tests (AC: #6)**
  - [ ] Commit a small but real `poetry.lock` fixture exercising both the legacy (`category`,
        `[metadata.files]`) and modern (`groups`, `[[package.files]]`) shapes. Parser test asserts exact pins
        and that every package is `unknown`; no subprocess/network.
  - [ ] Detection test for `poetry.lock`; consistency test stays green; `pixi run ci` green.

## Dev Notes

### The skip-resolution precedent (reuse this) — verified

Same as Story 15.1: `tasks/sbom_pipeline.py::resolve_transitive_deps` → `services.resolve_job_packages` →
`parsers.resolve_packages(format, content)` → the format's `resolve`. The lockfile short-circuit lives inside
the resolver (`pixi_lock.resolve` reads the solved set directly, no `uv_pip_compile`/subprocess/network).
`poetry.lock` follows the same shape — no pipeline/services change beyond `_RESOLVERS` registration.

### Direct/transitive decision — `unknown` (matches pixi.lock) — verified

`pixi_lock.resolve` leaves `relationship` at the `unknown` default; `test_pixi_lock_packages_are_unknown`
pins this ("the full solved env with no declared marker → all unknown; never guessed"). `poetry.lock` is the
same situation: the direct set is declared in `pyproject.toml [tool.poetry.dependencies]` /
`[tool.poetry.group.<g>.dependencies]`, which the lock does not carry. Since this story ingests the lock
alone (no paired `pyproject.toml`), tagging every package `unknown` is the correct, precedent-consistent
choice — rather than misusing `optional`/`groups` as a direct/transitive proxy (they encode extras/dev
grouping, not the direct graph). `_types.py` already defaults `relationship="unknown"`, so this is the no-op
default — do not call `tag_relationships`.

### poetry.lock schema (verify against the committed fixture)

TOML. `[[package]]` tables: `name`, `version`, `description`, `optional` (bool), `python-versions`, and either
`groups = ["main", "dev"]` (Poetry ≥ 1.5 / 2.x) or `category = "main"` (older). `[package.dependencies]` maps
edge names → constraints. Hashes: newer Poetry writes `[[package.files]]` (`{file, hash}`) inside each
package; older Poetry collects them under a top-level `[metadata.files]` map (name → list of `{file, hash}`).
`[metadata]` also has `lock-version`, `python-versions`, `content-hash`. Only `name` + `version` are
load-bearing for the pinned set; read hashes/files only if a downstream field consumes them.

### Detection specifics — verified

Anchored exact pattern `^poetry\.lock$` (filename lowercased before match). Distinct token → no collision.
Add `POETRY_LOCK` to the `tomllib` branch of `validate_parseable`.

### estimate_seconds / frontend / prose — verified

Same pattern as 15.1: `estimate_seconds` gets a lower `POETRY_LOCK` estimate (no resolution);
`manifestFormats.ts` gets `'poetry_lock'` in enum order (Story 6.4 consistency test —
`test_manifest_format_consistency.py`); `HomePage.tsx:35` upload copy + one-pager/docs count updated.

### Project Structure Notes

- Pure-function parser (AD-3): bytes in, `list[PackageSpec]` out, no I/O.
- Drive the parser test via `resolve_packages("poetry_lock", content)` (see `test_parsers.py`).

### References

- `backend/generate_sbom/manifests/models.py`, `backend/generate_sbom/manifests/detection.py`.
- `backend/generate_sbom/sbom/parsers/pixi_lock.py` (direct-read + `unknown` precedent),
  `sbom/parsers/_types.py`, `sbom/parsers/__init__.py`.
- `backend/generate_sbom/sbom/services.py` (`estimate_seconds`), `tasks/sbom_pipeline.py` (unchanged).
- `frontend/src/api/manifestFormats.ts`, `frontend/src/pages/HomePage.tsx`.
- `backend/tests/unit/test_manifest_format_consistency.py`, `backend/tests/unit/test_parsers.py`.
- Story 15.1 (`15-1-uv-lock-parser.md`) — shared lockfile-reader conventions.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
