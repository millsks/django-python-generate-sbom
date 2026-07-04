# Story 3.1: Manifest Upload & Format Detection

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Requirement Addition (2026-07-03) — provenance metadata (FR-3.8)

The upload form/serializer captures **four REQUIRED provenance fields**, persisted on `ManifestUpload`: `application_id` (free-text), `component_name`, `repository_url` (URL-validated), `source_branch` (free text, placeholder "main"). All four required. They are carried through to SBOM generation and embedded in the document metadata (Story 3.4, FR-4.4). See PRD FR-3.8, solution-design §3.2/§3.3, and memory manifest-provenance-metadata.

## Story

As a user,
I want to upload a Python manifest file that is validated and its format detected,
so that I can be confident the file will be processed correctly before a job is queued.

## Acceptance Criteria

1. Given the `ManifestUpload` model and a valid `requirements.txt` under 50 MB, when it is uploaded via `POST /api/v1/sbom/generate/` or the web UI, then the file is stored at `manifest-uploads/{org_id}/{upload_id}/{filename}`, a `ManifestUpload` record is created scoped to the org, and `detected_format` is set to `requirements` (FR-3.1).
2. Given a file whose name and structural markers match one of the five supported formats, when format detection runs, then the detection heuristic is applied in order: `pixi.lock` → `pixi.toml` → `pyproject.toml` (+`[tool.poetry]` note) → PEP 621 `pyproject.toml` → `environment.yml`/`.yaml` → `requirements*.txt` (FR-3.3).
3. Given an uploaded file with an unsupported extension (e.g., `Pipfile`), when validation runs, then the response is `400` with `{"error": "Unsupported manifest format. Supported: requirements.txt, pyproject.toml, pixi.lock, pixi.toml, environment.yml", "code": "unsupported_format"}` and no `ManifestUpload` or job is created (FR-3.2).
4. Given detection is ambiguous, when the request includes an optional `manifest_format` parameter, then the supplied format overrides automatic detection (FR-3.3).
5. Given a file exceeding 50 MB, when it is uploaded, then the response is `400` with a size-limit error before any storage write (FR-3.4).
6. Given any uploaded manifest, when its content is parsed during validation, then only safe loaders are used (`tomllib`, PyYAML safe load, `packaging`); no content reaches `eval`, `exec`, or a shell (FR-3.4, NFR-3.1).
7. Given a file that passes MIME and size checks but fails safe-parse (malformed content), when validation runs, then the response is `400` with a parse-error message and no task is enqueued (FR-3.4).
8. Given an upload attempting path traversal in the filename (e.g., `../../etc/passwd`), when the file is stored, then the filename is sanitized and the stored path stays within `manifest-uploads/{org_id}/{upload_id}/` (NFR-3.4).

## Tasks / Subtasks

- [ ] Task 1 — `ManifestUpload` model (AC: #1)
  - [ ] Add `manifests/models.py` `ManifestUpload(OrgScopedModel)` with fields: `user` FK, `file_key` (str, S3 path), `detected_format` (str), `original_filename` (str), `uploaded_at` (datetime); PK is UUID
  - [ ] `OrgScopedModel` (from Story 1.3) supplies the `org` FK and `OrgScopedManager` — do not re-add `org`
  - [ ] Generate migration for `ManifestUpload`
- [ ] Task 2 — Format detection service (AC: #2, #4)
  - [ ] Implement `manifests/services.py` detection applying the heuristic IN ORDER (see Dev Notes → Format detection); return one of `requirements|pyproject|pixi_lock|pixi_toml|conda`
  - [ ] Detection reads filename first, then structural markers (`[tool.poetry]` in pyproject); do not rely on extension alone
  - [ ] Honor an optional `manifest_format` override parameter when supplied
- [ ] Task 3 — Upload + validation service (AC: #1, #5, #6, #7, #8)
  - [ ] `upload_manifest(org, user, file_obj, filename)` validates size (≤50 MB) BEFORE any storage write, checks MIME, sanitizes the filename (strip path components), then safe-parses to confirm the content is loadable
  - [ ] Store to `manifest-uploads/{org_id}/{upload_id}/{filename}` via `django-storages` default_storage
  - [ ] Use only `tomllib` / PyYAML `safe_load` / `packaging` — never `eval`, `exec`, `yaml.load` (unsafe), or shell (NFR-3.1)
  - [ ] Return the created `ManifestUpload`
- [ ] Task 4 — Upload endpoint wiring (AC: #1, #3)
  - [ ] Wire `POST /api/v1/manifests/upload/` (per solution-design §3.2) returning `{upload_id, detected_format}`; note the generate endpoint `POST /api/v1/sbom/generate/` (Story 3.2) also drives upload+detect in one call
  - [ ] Unsupported format → `400` with the exact error envelope in AC #3 (`code: unsupported_format`)
  - [ ] `views.py` = DRF view only; all logic in `services.py`/`selectors.py` (file-roles convention)
- [ ] Task 5 — Selector (AC: #1)
  - [ ] `manifests/selectors.py` `get_manifest(org, upload_id)` using `.for_org(org)` → 404 semantics on cross-org (AD-2)
- [ ] Task 6 — Tests (AC: all)
  - [ ] Unit: detection returns correct format for each of the 5 fixture types + poetry-vs-PEP621 disambiguation + override
  - [ ] Unit: >50MB rejected before write; malformed content → 400; unsupported ext → 400 with exact envelope
  - [ ] Unit: path-traversal filename sanitized; stored path stays under the org/upload prefix
  - [ ] Integration: real upload to test MinIO bucket produces the expected `file_key` and DB row
  - [ ] Maintain ≥90% coverage; `pixi run ci` exits 0

## Dev Notes

### `ManifestUpload` model (solution-design.md §3.2)

```python
class ManifestUpload(OrgScopedModel):
    # OrgScopedModel adds: org (FK), objects = OrgScopedManager()
    user: FK(User)
    file_key: str          # manifest-uploads/{org_id}/{upload_id}/{filename}
    detected_format: str   # 'requirements' | 'pyproject' | 'pixi_lock' | 'pixi_toml' | 'conda'
    original_filename: str
    uploaded_at: datetime
```

### Format detection — apply IN THIS ORDER (solution-design.md §3.2; addendum)

1. filename `pixi.lock` → `pixi_lock` (**YAML** despite `.lock` — parsed with PyYAML `safe_load`, NOT `tomllib`)
2. filename `pixi.toml` → `pixi_toml`
3. filename `pyproject.toml` containing `[tool.poetry]` → `pyproject` (Poetry variant; Poetry lockfile support is v2)
4. filename `pyproject.toml` (PEP 621) → `pyproject`
5. filename `environment.yml` / `environment.yaml` → `conda`
6. filename matching `requirements*.txt` → `requirements`

Extension alone is insufficient — structural markers disambiguate pyproject variants. Detection order is load-bearing; a `pixi.lock` must never fall through to a TOML parser.

### Validation guardrails (FR-3.4, NFR-3.1, NFR-3.4)

- Size check (≤50 MB) happens BEFORE storage write — reject large files without spending storage IO.
- Safe loaders ONLY: `tomllib`, PyYAML `safe_load`, `packaging.requirements.Requirement`. Never `eval`/`exec`/`yaml.load`/shell with file content.
- Sanitize filename against path traversal; the stored key is always `manifest-uploads/{org_id}/{upload_id}/{sanitized_filename}`. Zip bombs / traversal rejected (NFR-3.4).

### Storage path (spine Consistency Conventions; solution-design.md §6.1)

`manifest-uploads/{org_id}/{upload_id}/{original_filename}` via `django-storages` (MinIO local / S3 prod). Blob lives only in object storage; only `file_key` is in PostgreSQL (AD-6).

### Org scoping (AD-2)

`ManifestUpload` extends `OrgScopedModel`; all reads use `.for_org(org)`. Views read `org = request.auth.org` and pass it as the first positional arg to services/selectors (AD-3). Cross-org access returns `404` at the API.

### Project Structure Notes

- New app module: `<project_slug>/manifests/` with `models.py`, `services.py`, `selectors.py`, `views.py`, `migrations/`.
- Depends on Story 1.3 (`OrgScopedModel`, `users.Org`, settings/storage) and Story 1.1 (scaffold). The full generate endpoint (`POST /api/v1/sbom/generate/`) is completed in Story 3.2, which reuses this upload+detect service; keep the upload service reusable and view-agnostic.
- No SBOMJob here — that model and the concurrency gate are Story 3.2.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1: Manifest Upload & Format Detection]
- [Source: solution-design.md#3.2 manifests/]
- [Source: solution-design.md#6.1 Storage paths]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: ARCHITECTURE-SPINE.md#AD-3 — Service layer purity]
- [Source: ARCHITECTURE-SPINE.md#AD-6 — Storage triad]
- [Source: PRD addendum.md#Manifest Parser Implementation Notes]
- [Source: prd.md#FR-3.1, FR-3.2, FR-3.3, FR-3.4, NFR-3.1, NFR-3.4]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
