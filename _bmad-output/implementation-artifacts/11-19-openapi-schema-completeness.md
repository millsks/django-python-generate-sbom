# Story 11.19: OpenAPI/Swagger Schema Completeness (Request Bodies + Parameters)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Implement against the **then-current merged state** — at minimum the full endpoint set through **Story 13.1**. **Recommended:** run after Stories 2.18–2.20 merge so any demote/route/access-scope changes are captured in one pass. This story reconciles the **generated OpenAPI schema** (what Swagger UI renders), not the markdown API reference — that is Story 11.16's job. Keep the two consistent.

## Story

As an API consumer using the Swagger UI,
I want every endpoint in the generated OpenAPI schema to declare its request body, path/query parameters, and response shapes,
so that "Try it out" shows input fields for the payload and parameters instead of an empty form, and I can exercise the API accurately from the docs.

## Background

The interactive docs (drf-spectacular schema at `/api/schema/`, Swagger UI at `/api/docs/`, ReDoc at `/api/redoc/`) were wired in Story 11.9. Most mutating endpoints are hand-rolled `APIView`s whose `.post()`/`.delete()` methods either read `request.data` directly or instantiate a serializer manually (`SomeSerializer(data=request.data)`). drf-spectacular's `AutoSchema` **cannot infer a request body** from a bare `APIView` method — it only reads `serializer_class`/`get_serializer` (which these views don't define) or an explicit `@extend_schema(request=…)`. The result: these operations render in Swagger with **no requestBody**, so "Try it out" exposes no input fields. Two endpoints (`orgs/switch/`, `sbom/jobs/artifacts/bulk-delete/`) have **no serializer at all** — they read `request.data` dict keys directly, so their payload is completely invisible. Custom query filters (`?status=`, `?format=` on the jobs list) read from `request.query_params` are also undeclared. Inline-dict responses across the GET endpoints have no response schema.

This story audits the generated schema and attaches `@extend_schema(request=…, parameters=[…], responses=…)` (or a `serializer_class`) to every endpoint so the schema is complete.

## Acceptance Criteria

1. **Every mutating endpoint declares a request body.** Each `POST`/`PUT`/`PATCH` operation in the generated schema (`/api/schema/`) that accepts a payload declares a `requestBody` whose schema exposes the payload fields, so Swagger UI "Try it out" renders input fields. This covers the bare-`APIView` POSTs that currently instantiate a serializer manually (register, login, orgs/create, orgs/switch, promote-admin, members add, members create-user, keys create, global-admins grant, manifests/upload, sbom/generate, bulk-delete) — including the two endpoints with **no serializer today** (`orgs/switch/`, `sbom/jobs/artifacts/bulk-delete/`), for which a request serializer is authored (or an inline `@extend_schema` request schema is supplied). Multipart/file uploads (`manifests/upload/`, `sbom/generate/`) declare `multipart/form-data` with the file field. (FR-DOC9)
2. **Every parameterized endpoint declares its parameters.** Each path parameter (`<int:user_id>`, `<str:key_id>`, `<uuid:task_id>`) is present and typed in the operation's `parameters`, and each custom query filter (`status`, `format` on `GET /sbom/jobs/`; confirm pagination `page`/`page_size` surface via the pagination class) is declared via `OpenApiParameter`, so Swagger "Try it out" renders the corresponding inputs.
3. **Responses carry accurate schemas.** Each operation declares response schemas for its success status (including non-200 successes: `201` created, `202` accepted, `204` no-content, `303` redirect) and the meaningful error shapes (the `{error, code}` envelope for `400`/`403`/`404`/`429`) where they are part of the contract. Endpoints returning inline dicts/lists (e.g. `auth/me`, `orgs/`, `sbom/status`, `sbom/document`, the report views) expose a response schema rather than an empty/undocumented response.
4. **A schema-level test proves the gap is closed.** A unit test generates the OpenAPI schema in-process (no live server, no network) and asserts that the previously-missing endpoints now declare a `requestBody` and/or `parameters` — at minimum: `orgs/switch/` and `sbom/jobs/artifacts/bulk-delete/` declare a request body; `sbom/generate/` and `manifests/upload/` declare a multipart request body; `GET /sbom/jobs/` declares the `status` and `format` query parameters; a representative parameterized GET (e.g. `sbom/status/{task_id}`) declares its path parameter. The test lives in `backend/tests/unit/` alongside `test_api_schema.py`.
5. **No new schema generation warnings; docs build green.** Generating the schema produces no new drf-spectacular warnings for the touched endpoints (run with warnings surfaced), and `pixi run ci` is green including `docs-build` (`mkdocs build --strict`).

## Tasks / Subtasks

- [ ] **Task 1 — Audit the generated schema (AC: #1, #2, #3)**
  - [ ] Generate the schema in-process (e.g. `drf_spectacular.generators.SchemaGenerator().get_schema(request=None, public=True)` or `GET /api/schema/?format=json`) and enumerate every operation.
  - [ ] For each operation, record: has requestBody? path params present/typed? query params declared? response schema present? Confirm against the inventory table in Dev Notes and reconcile any drift from the then-current merged code.
- [ ] **Task 2 — Attach request bodies (AC: #1)**
  - [ ] Add `@extend_schema(request=<Serializer>, responses=…)` to each bare-`APIView` POST that manually builds a serializer (register, login, orgs/create, promote-admin, members add, members create-user, keys create, global-admins grant, manifests/upload, sbom/generate).
  - [ ] Author request serializers for the two endpoints with none today: `OrgSwitchView` (`{slug}`) and `BulkDeleteArtifactsView` (`{all?, task_ids?}`); wire them into the views (or declare inline via `@extend_schema`). Multipart uploads declare `multipart/form-data`.
- [ ] **Task 3 — Declare parameters (AC: #2)**
  - [ ] Add `OpenApiParameter` entries for the `status` and `format` query filters on `GET /sbom/jobs/`; confirm pagination params surface. Verify path params (`user_id`, `key_id`, `task_id`) appear typed on every parameterized operation; add `OpenApiParameter(location=PATH)` where description/type polish is needed.
- [ ] **Task 4 — Response schemas (AC: #3)**
  - [ ] Declare `responses={…}` for each operation's success + meaningful error shapes, using inline serializers / `OpenApiResponse` for the inline-dict responses (`auth/me`, `orgs/`, `orgs/me`, `sbom/status`, `sbom/document`, report views, key/member list shapes).
- [ ] **Task 5 — Schema-level test (AC: #4)**
  - [ ] Add a unit test in `backend/tests/unit/` that builds the schema in-process and asserts requestBody/parameters on the previously-missing endpoints. No network, no live server.
- [ ] **Task 6 — Verify (AC: #5)**
  - [ ] Confirm no new spectacular warnings for touched endpoints; `pixi run ci` green including `docs-build`.

## Dev Notes

### Endpoint inventory (verified in code — reconcile against merged state before finalizing)

Legend for "Missing": **REQ** = no request body in schema (bare `APIView`, serializer built manually or absent); **REQ!** = no serializer exists at all (reads `request.data` directly); **QP** = custom query param undeclared; **RESP** = inline response has no schema; **PATH** = path param (usually resolved from URLconf — verify typed/described).

#### users app — `backend/generate_sbom/users/views.py` + `urls.py` (mounted `/api/v1/`)

| Method + path | View | Missing | Fix |
| --- | --- | --- | --- |
| `POST /auth/register/` | `RegisterView` | REQ, RESP | `@extend_schema(request=RegistrationSerializer, responses={201: …})` |
| `POST /auth/login/` | `LoginView` | REQ, RESP | `request=LoginSerializer, responses={200, 400, 401}` |
| `POST /auth/logout/` | `LogoutView` | RESP | `responses={204: None}` (no body needed) |
| `GET /auth/me/` | `AuthMeView` | RESP | inline response serializer `{id, email, is_admin, is_global_admin}` |
| `GET /orgs/` | `OrgListView` | RESP | list response schema `{slug, name, active}[]` |
| `POST /orgs/create/` | `CreateOrgView` | REQ, RESP | `request=CreateOrgSerializer, responses={201, 403}` |
| `POST /orgs/switch/` | `OrgSwitchView` | **REQ!**, RESP | author `OrgSwitchSerializer{slug}`; `responses={200, 403}` |
| `GET /orgs/me/` | `OrgMeView` | RESP | response `{slug, name}`; `404` no-active-org |
| `POST /orgs/leave/` | `LeaveOrgView` | RESP | `responses={204, 404}` |
| `POST /orgs/promote-admin/` | `PromoteAdminView` | REQ, RESP | `request=UserIdSerializer, responses={204, 403, 404}` |
| `GET /orgs/members/` | `MembersView` | RESP | response `{members[], is_admin}`; `403` |
| `POST /orgs/members/` | `MembersView` | REQ, RESP | `request=AddMemberSerializer, responses={201, 400(no_such_user), 403}` |
| `POST /orgs/members/create-user/` | `CreateMemberUserView` | REQ, RESP | `request=CreateMemberUserSerializer, responses={201, 400(email_taken), 403}` |
| `DELETE /orgs/members/<int:user_id>/` | `MemberDetailView` | PATH, RESP | `parameters=[user_id]`; `responses={204, 403, 404}` |
| `GET /keys/` | `KeysView` | RESP | key-list response schema |
| `POST /keys/` | `KeysView` | REQ, RESP | `request=CreateKeySerializer, responses={201, 403}` (plaintext returned once) |
| `DELETE /keys/<str:key_id>/` | `KeyDetailView` | PATH, RESP | `parameters=[key_id]`; `responses={204, 403, 404}` |
| `GET /admin/global-admins/` | `GlobalAdminsView` | RESP | response `{global_admins[]}`; `403` |
| `POST /admin/global-admins/` | `GlobalAdminsView` | REQ, RESP | `request=AddMemberSerializer` (grant by email); `responses={201, 400, 403}` |
| `DELETE /admin/global-admins/<int:user_id>/` | `GlobalAdminDetailView` | PATH, RESP | `parameters=[user_id]`; `responses={204, 400(last_global_admin), 403, 404}` |

#### manifests app — `backend/generate_sbom/manifests/views.py`

| Method + path | View | Missing | Fix |
| --- | --- | --- | --- |
| `POST /manifests/upload/` | `ManifestUploadView` | REQ (multipart), RESP | `@extend_schema(request=ManifestUploadSerializer, responses={201, 400})`; multipart/form-data with `file` + provenance fields |

#### sbom app — `backend/generate_sbom/sbom/views.py`

| Method + path | View | Missing | Fix |
| --- | --- | --- | --- |
| `POST /sbom/generate/` | `GenerateJobView` | REQ (multipart), RESP | `request=GenerateJobSerializer, responses={202, 400, 429}` |
| `GET /sbom/jobs/` | `JobsListView` (`ListAPIView`) | QP | response inferred from `JobListSerializer` + pagination; add `OpenApiParameter` for `status`, `format` query filters |
| `GET /sbom/status/<uuid:task_id>/` | `StatusJobView` | PATH, RESP | `parameters=[task_id]`; status response schema; `404` |
| `GET /sbom/result/<uuid:task_id>/` | `ResultJobView` | PATH, RESP | `parameters=[task_id]`; `responses={303, 404}` (303 → presigned URL) |
| `GET /sbom/document/<uuid:task_id>/` | `SbomDocumentView` | PATH, RESP | `parameters=[task_id]`; `{format, metadata, components, raw}`; `404` |
| `DELETE /sbom/jobs/<uuid:task_id>/artifacts/` | `JobArtifactsView` | PATH, RESP | `parameters=[task_id]`; `{task_id, deleted}`; `404` |
| `POST /sbom/jobs/artifacts/bulk-delete/` | `BulkDeleteArtifactsView` | **REQ!**, RESP | author serializer `{all?: bool, task_ids?: uuid[]}`; `responses={200, 400, 403}` |

#### analysis app — `backend/generate_sbom/analysis/views.py`

| Method + path | View | Missing | Fix |
| --- | --- | --- | --- |
| `GET /sbom/result/<uuid:task_id>/reports/vulnerabilities/` | `VulnerabilityReportView` | PATH, RESP | `parameters=[task_id]`; report JSON response; `404` (not_ready/report_failed) |
| `GET /sbom/result/<uuid:task_id>/reports/licenses/` | `LicenseReportView` | PATH, RESP | same |
| `GET /sbom/result/<uuid:task_id>/reports/versions/` | `VersionReportView` | PATH, RESP | same |
| `GET /sbom/result/<uuid:task_id>/reports/graph/` | `GraphReportView` | PATH, RESP | `parameters=[task_id]`; `{nodes, edges}`; `404` |
| `GET /sbom/result/<uuid:task_id>/reports/graph/download/` | `GraphSvgDownloadView` | PATH, RESP | `parameters=[task_id]`; `responses={303, 404}` |

### Why bare `APIView` produces an empty request body

drf-spectacular's `AutoSchema.get_request_serializer()` looks for `view.get_serializer()`/`serializer_class`, then falls back to the `@extend_schema(request=…)` override. These views define neither on the method that reads the payload — they call `Serializer(data=request.data)` **inside** `post()`, which is opaque to static schema generation. So the operation is emitted with **no `requestBody`**, and Swagger "Try it out" shows no fields. Path parameters, by contrast, are resolved from the URLconf and usually appear (typed by the path converter), but query params read from `request.query_params` and any request body are invisible without an explicit annotation. The two "REQ!" endpoints (`orgs/switch/`, `bulk-delete`) read `request.data` dict keys with no serializer anywhere, so they are the most opaque — author a serializer for each so the payload is both validated and documented.

### Existing serializers to reuse (`backend/generate_sbom/users/serializers.py`)

`RegistrationSerializer`, `LoginSerializer`, `CreateOrgSerializer`, `AddMemberSerializer` (email — reused for members-add and grant-global-admin), `CreateMemberUserSerializer`, `UserIdSerializer` (promote-admin), `CreateKeySerializer`. sbom/manifests: `GenerateJobSerializer`, `JobListSerializer`, `ManifestUploadSerializer`. New serializers needed: **`OrgSwitchSerializer{slug}`** and a **bulk-delete request serializer `{all?: bool, task_ids?: uuid[]}`** (mutually-exclusive semantics documented in the description).

### Schema test approach (AC #4 — no network)

`test_api_schema.py` already exercises `/api/schema/` via the Django test `Client` (in-process, no live server). Extend that pattern: fetch `GET /api/schema/?format=json` (or call `SchemaGenerator().get_schema(request=None, public=True)`) and assert on `schema["paths"][<path>][<method>]` for `requestBody` / `parameters`. Assert the two REQ! endpoints and the two multipart endpoints now carry a `requestBody`, and that `GET /sbom/jobs/` lists the `status`/`format` query params. Keep it a unit test in `backend/tests/unit/`.

### Scope / coordination

- **Schema (code) reconciliation only** — this story edits DRF views/serializers so the *generated* OpenAPI schema is complete. The markdown API reference (`docs/api/*.md`) is **Story 11.16**; keep the request/response shapes documented there consistent with what the schema now emits (spectacular is the source of truth — reconcile prose to it, not the reverse).
- Implement against the **then-current merged state** (at minimum through Story 13.1; recommended after 2.18–2.20 so any demote/route/access changes to `orgs`/`admin` endpoints are captured). Re-run the audit against the live code before finalizing — codes/messages/endpoints may have been refined.

### Project Structure Notes

- Views/serializers under `backend/generate_sbom/{users,manifests,sbom,analysis}/`. Schema config in `backend/config/settings/base.py` (`SPECTACULAR_SETTINGS`, `API_DOCS_ENABLED`) and URL wiring in `backend/config/urls.py` (Story 11.9). Auth-scheme extension in `backend/generate_sbom/users/schema.py`.
- Tests: `backend/tests/unit/test_api_schema.py` (existing Story 11.9 coverage). Gate: `pixi run ci` (includes `docs-build` = `mkdocs build --strict`).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 11.19]
- Code (views): `backend/generate_sbom/users/views.py`, `backend/generate_sbom/sbom/views.py`, `backend/generate_sbom/manifests/views.py`, `backend/generate_sbom/analysis/views.py`
- Code (serializers): `backend/generate_sbom/users/serializers.py`, `backend/generate_sbom/sbom/serializers.py`, `backend/generate_sbom/manifests/serializers.py`
- Code (URLconf): `backend/generate_sbom/{users,sbom,manifests,analysis}/urls.py`, `backend/config/urls.py`
- Schema config: `backend/config/settings/base.py` (`SPECTACULAR_SETTINGS`), `backend/generate_sbom/users/schema.py`
- Tests: `backend/tests/unit/test_api_schema.py`
- Companion (markdown API reference): Story 11.16 (`11-16-api-reference-and-openapi-reconciliation-admin-tier.md`); origin of Swagger wiring: Story 11.9.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
