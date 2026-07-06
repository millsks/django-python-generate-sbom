# Story 15.3: Pipfile.lock Parser

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement after **Stories 15.1 and 15.2**. This is the last Epic 15 story — it flips the
> supported-format count to **8**. Reuses the shared lockfile-reader conventions from 15.1.

## Story

As a user,
I want to upload a `Pipfile.lock` file,
so that I get an SBOM built from its exact pinned closure without the app re-resolving anything.

## Acceptance Criteria

1. **Detection.** A file named `Pipfile.lock` is detected as a new `ManifestUpload.Format.PIPFILE_LOCK` via an
   exact-match filename pattern in `manifests/detection.py` (matched case-insensitively — detection lowercases
   the name to `pipfile.lock`); `validate_parseable` safe-parses it as **JSON** (`json.loads`, a new branch
   alongside the TOML/YAML branches); and the `SUPPORTED` string lists `Pipfile.lock`.
2. **Direct-read parser (skip resolution).** A new `sbom/parsers/pipfile_lock.py`
   `resolve(content) -> list[PackageSpec]` reads every entry under `default` and `develop` into a pinned
   `PackageSpec` (name + the exact version parsed from the `"==x.y.z"` pin, PyPI ecosystem) **with no
   re-resolution** — no subprocess, no network — reusing the 15.1 conventions. Entries lacking a `version`
   (VCS/editable installs) are tolerated (skipped, or version left blank — not a crash). It is registered in
   `sbom/parsers/__init__.py` `_RESOLVERS` under `PIPFILE_LOCK`.
3. **Direct vs transitive — all `unknown` (justified).** `Pipfile.lock`'s `default`/`develop` sections each
   hold the **full** closure (direct + transitive) with no per-package direct marker (the direct set lives in
   the `Pipfile`, not the lock). Therefore every package is recorded as resolved with relationship `unknown`
   (the `pixi.lock` precedent). The `default` vs `develop` split (runtime vs dev group) is read but — like
   `poetry.lock`'s groups — is **not** treated as a direct/transitive signal.
4. **Enum + migration + wiring.** `ManifestUpload.Format` gains `PIPFILE_LOCK = "pipfile_lock", "Pipfile.lock"`;
   a Django `manifests` migration is generated (choice-only `AlterField`; `pipfile_lock` = 12 chars, fits
   `max_length=20`). `estimate_seconds` gains a `PIPFILE_LOCK` entry reflecting the skipped resolution step.
5. **Frontend + prose (count → 8).** `frontend/src/api/manifestFormats.ts` `MANIFEST_FORMATS` gains
   `'pipfile_lock'` in enum order; the upload copy (`frontend/src/pages/HomePage.tsx`) and the
   supported-format prose/count — now **8 Python package formats** — in `one-pager.md`,
   `docs/how-to/generate-sbom.md`, `docs/index.md` are updated to include `Pipfile.lock`. The Story 6.4
   consistency test stays green.
6. **Tests + gate.** `pixi run ci` is green (backend coverage ≥90%) with: a parser unit test against a
   committed real `Pipfile.lock` fixture (self-contained, no network) asserting the pinned set across
   `default` + `develop` and tolerating a version-less entry; a detection test (including the mixed-case
   `Pipfile.lock` name); and the manifest-format consistency test kept passing.

## Tasks / Subtasks

- [ ] **Task 1 — Detection (AC: #1)**
  - [ ] `manifests/detection.py`: add `(re.compile(r"^pipfile\.lock$"), _Format.PIPFILE_LOCK)` to
        `_FORMAT_PATTERNS` (name is already lowercased in `detect_format`); append `Pipfile.lock` to
        `SUPPORTED`.
  - [ ] `validate_parseable`: add a JSON branch (`import json`; `json.loads(text)` catching
        `json.JSONDecodeError` → `ManifestParseError`) for `PIPFILE_LOCK`.
- [ ] **Task 2 — Enum + migration (AC: #4)**
  - [ ] `manifests/models.py`: add `PIPFILE_LOCK = "pipfile_lock", "Pipfile.lock"`.
  - [ ] `pixi run` `makemigrations manifests` → commit the migration.
- [ ] **Task 3 — Parser (AC: #2, #3)**
  - [ ] New `sbom/parsers/pipfile_lock.py`: `json.loads`; guard bad-JSON / non-dict with `ResolutionError`.
  - [ ] Iterate `default` then `develop`; for each `{name: {version, hashes, ...}}` emit a `PackageSpec`
        (`name`, version parsed from the leading `==` of the `version` string, `ecosystem=PYPI`). Skip / blank
        entries with no `version` (VCS/editable/local). Leave `relationship` at the `unknown` default.
  - [ ] Reuse the 15.1 `_lockfile.py` helper(s) where applicable. Register `PIPFILE_LOCK: pipfile_lock.resolve`
        in `_RESOLVERS`.
- [ ] **Task 4 — Estimate + frontend + prose (AC: #4, #5)**
  - [ ] `estimate_seconds`: add a `PIPFILE_LOCK` branch (lockfile → no resolution).
  - [ ] `manifestFormats.ts`: add `'pipfile_lock'` in enum order; update `HomePage.tsx` copy; update the
        supported-format count to **8** in the one-pager + docs how-to/index.
- [ ] **Task 5 — Tests (AC: #6)**
  - [ ] Commit a small but real `Pipfile.lock` fixture with `default` + `develop` sections and one
        version-less (VCS) entry. Parser test asserts exact pins across both sections, that the version-less
        entry is handled, and that every package is `unknown`; no subprocess/network.
  - [ ] Detection test asserting `Pipfile.lock` (mixed case) detects as `pipfile_lock`; consistency test stays
        green; `pixi run ci` green.

## Dev Notes

### The skip-resolution precedent (reuse this) — verified

Same as 15.1/15.2: the pipeline is unchanged; `parsers.resolve_packages("pipfile_lock", content)` dispatches
to `pipfile_lock.resolve`, which reads the pins directly (no `uv_pip_compile`, no subprocess, no network),
mirroring `pixi_lock.resolve`.

### Direct/transitive decision — `unknown` (matches pixi.lock) — verified

pipenv locks the **entire** resolved graph into `default` (runtime) and `develop` (dev); there is no
per-package direct/transitive marker in the lock (the direct set is the `Pipfile`, absent here). Consistent
with `pixi_lock` and Story 15.2, every package is left at the `unknown` default (`_types.py` default;
`test_pixi_lock_packages_are_unknown` is the precedent). The `default`/`develop` split is a runtime-vs-dev
group signal, not a direct/transitive one — do not conflate them.

### Pipfile.lock schema (verify against the committed fixture)

JSON (**not** TOML/YAML — this is the first JSON manifest, so `validate_parseable` needs a new branch):

```json
{
  "_meta": { "hash": {"sha256": "..."}, "pipfile-spec": 6, "requires": {"python_version": "3.12"},
             "sources": [{"name": "pypi", "url": "https://pypi.org/simple", "verify_ssl": true}] },
  "default": { "requests": { "hashes": ["sha256:...", "sha256:..."], "index": "pypi", "version": "==2.31.0" } },
  "develop": { "pytest":   { "hashes": ["sha256:..."], "version": "==7.4.0" } }
}
```

Versions are exact-pinned as a `"==x.y.z"` string — strip the leading `==`. Some entries have no `version`
(VCS refs via `"git"`/`"ref"`, or `"editable": true` local paths); tolerate them (skip or blank version).
`markers` may appear per package (carry only if a downstream field exists). Load-bearing output: name + exact
version + PyPI ecosystem.

### Detection specifics — verified

`detect_format` lowercases the filename, so `Pipfile.lock` → `pipfile.lock`; anchored pattern
`^pipfile\.lock$` matches it. Distinct token → no collision with existing patterns. The **new JSON branch** in
`validate_parseable` is the one behavior this format adds beyond 15.1/15.2 (which are TOML like the existing
TOML manifests).

### estimate_seconds / frontend / prose — verified

Same pattern as 15.1/15.2. This story is the last of Epic 15, so it flips the supported-format count from 5 to
**8** wherever it appears (one-pager "5 Python package formats"; the docs how-to/index format lists).
`manifestFormats.ts` gets `'pipfile_lock'` in enum order (Story 6.4 consistency test).

### Project Structure Notes

- Pure-function parser (AD-3): bytes in, `list[PackageSpec]` out, no I/O.
- Drive the parser test via `resolve_packages("pipfile_lock", content)` (see `test_parsers.py`).

### References

- `backend/generate_sbom/manifests/models.py`, `backend/generate_sbom/manifests/detection.py`
  (`validate_parseable` — add the JSON branch).
- `backend/generate_sbom/sbom/parsers/pixi_lock.py` (direct-read + `unknown` precedent),
  `sbom/parsers/_types.py`, `sbom/parsers/__init__.py`.
- `backend/generate_sbom/sbom/services.py` (`estimate_seconds`), `tasks/sbom_pipeline.py` (unchanged).
- `frontend/src/api/manifestFormats.ts`, `frontend/src/pages/HomePage.tsx`.
- `backend/tests/unit/test_manifest_format_consistency.py`, `backend/tests/unit/test_parsers.py`.
- Stories 15.1 (`15-1-uv-lock-parser.md`) and 15.2 (`15-2-poetry-lock-parser.md`).

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
