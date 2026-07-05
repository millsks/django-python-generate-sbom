# Story 11.9: OpenAPI Schema & Swagger UI Endpoint

Status: review

## Story

As a developer integrating with the API,
I want interactive Swagger/OpenAPI docs served by the app at a standard endpoint,
so that I can explore and try the REST API live without reading source or hand-written docs.

## Acceptance Criteria

1. `drf-spectacular` generates an OpenAPI 3 schema from the live viewsets/serializers, served at `/api/schema/` (FR-DOC9).
2. Interactive Swagger UI at `/api/docs/` and ReDoc at `/api/redoc/`; UI assets self-hosted via `drf-spectacular-sidecar` (no external CDN).
3. The schema reflects the real auth schemes (session + Api-Key), groups endpoints with tags, and sets title/description/version via `SPECTACULAR_SETTINGS`; `DEFAULT_SCHEMA_CLASS` is drf-spectacular's `AutoSchema`.
4. Docs/schema endpoint exposure is deliberate — available in development, and its availability in production is configurable (`API_DOCS_ENABLED`), not accidentally always-public.
5. The Story 11.5 API reference and docs site link to the live Swagger UI; a test asserts the schema and Swagger-UI endpoints return 200 with a valid schema.

## Dev Notes

drf-spectacular + drf-spectacular-sidecar added as conda-forge runtime deps. `DEFAULT_SCHEMA_CLASS` set to `drf_spectacular.openapi.AutoSchema`; `SPECTACULAR_SETTINGS` sets title/description/version, `SERVE_INCLUDE_SCHEMA=False`, `SERVE_PERMISSIONS=[AllowAny]`, and `SWAGGER_UI_DIST/SWAGGER_UI_FAVICON_HREF/REDOC_DIST = "SIDECAR"` for self-hosted assets. The custom `OrgApiKeyAuthentication` is described to the schema via an `OpenApiAuthenticationExtension` (`users/schema.py`), registered in `UsersConfig.ready`. Endpoints are registered in `config/urls.py` only when `settings.API_DOCS_ENABLED` (base default `True`; `production.py` default `False`, both env-overridable) and sit ahead of the SPA catch-all (whose `api/` exclusion already keeps them clear). Story 11.5 will link the reference to the live UI.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Added `drf-spectacular` and `drf-spectacular-sidecar` (conda-forge) to `[dependencies]`.
- Wired `DEFAULT_SCHEMA_CLASS`, `SPECTACULAR_SETTINGS`, and `API_DOCS_ENABLED` in `config/settings/base.py`; `production.py` defaults `API_DOCS_ENABLED` off.
- Endpoints `/api/schema/`, `/api/docs/`, `/api/redoc/` registered in `config/urls.py` (gated), kept ahead of the SPA catch-all.
- `OpenApiAuthenticationExtension` for the Api-Key scheme in `generate_sbom/users/schema.py`, imported from `UsersConfig.ready`.
- 5 tests in `tests/unit/test_api_schema.py` (valid schema, Api-Key security scheme, Swagger UI 200, ReDoc 200, disabled-when-off 404).
- `pixi run ci` exits 0; backend coverage 94.02% (267 tests), frontend 94 tests.

### File List

- backend/config/settings/base.py
- backend/config/settings/production.py
- backend/config/urls.py
- backend/generate_sbom/users/apps.py
- backend/generate_sbom/users/schema.py
- backend/tests/unit/test_api_schema.py
- pixi.toml
- pixi.lock
