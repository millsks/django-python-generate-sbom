# Story 11.20: API Docs (Swagger UI) Link in the App Header — Env-Gated

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Implement against the **then-current merged state**. Builds directly on **Story 11.8** (the two existing header icon-links: Documentation + GitHub) and **Story 11.9** (the Swagger UI endpoint at `/api/docs/`, gated by `settings.API_DOCS_ENABLED`). Coordinate with **Story 11.19** (schema completeness) if it lands first — no file overlap expected, but the Swagger UI this link opens should be the polished one. Verify the header renders and `/api/docs/` responds (or 404s) as expected against the running app before finalizing.

## Story

As a developer using the app,
I want a link to the interactive API docs (Swagger UI) in the header alongside the Documentation and GitHub links,
so that I can jump straight to the live API explorer — but only on deployments where those docs are actually enabled.

## Acceptance Criteria

1. **An API-docs icon-link sits next to the existing header links.** The app header (Epic 10 shell, `frontend/src/components/Layout.tsx`) renders a third external icon-link — an **API/schema icon** from `@mui/icons-material` (e.g. `Api` or `IntegrationInstructions`) — immediately adjacent to the existing Documentation (`MenuBook`) and GitHub icon-links added by Story 11.8. It reuses the same `ExternalIconLink` pattern: MUI `IconButton` + `Tooltip`, `target="_blank"` + `rel="noopener noreferrer"`, and an accessible label/tooltip ("API docs" / "API documentation").

   **Given** the app header renders in either auth state (anon or authed) on a deployment where API docs are enabled,
   **When** the toolbar paints,
   **Then** an API-docs icon-link pointing at `/api/docs/` appears next to the Documentation and GitHub links and opens the Swagger UI in a new tab.

2. **The link is present ONLY when the flag is true, and completely absent otherwise.** The link element is conditionally rendered — not merely hidden/disabled. When the flag is false or unset, no icon, tooltip, or anchor for API docs exists in the DOM.

   **Given** the API-docs flag resolves to `false` (or is unset),
   **When** the header renders,
   **Then** no API-docs icon-link is present at all (the Documentation and GitHub links are unaffected).

3. **The flag single-sources the same setting that gates the `/api/docs/` endpoint, so the link and the endpoint enable together.** The chosen mechanism (see Dev Notes) surfaces the backend's existing `API_DOCS_ENABLED` setting to the SPA. The recommended approach is a small **public runtime config endpoint** so the link never points at a 404 and a Docker deploy can toggle both with one env var without rebuilding the frontend image.

   **Given** the backend already gates `/api/docs/` behind `settings.API_DOCS_ENABLED` (Story 11.9),
   **When** the frontend decides whether to show the link,
   **Then** it derives that decision from the **same** flag value — the link is shown exactly when the endpoint is served, and never points at a disabled (404) endpoint.

4. **Tests cover both states (and the config source if one is added).**

   **Given** the flag source is mocked to `true`,
   **When** `Layout` renders,
   **Then** a test asserts the API-docs link is present with `href="/api/docs/"`, `target="_blank"`, `rel` containing `noopener`, and the accessible label — in both auth states.

   **Given** the flag source is mocked to `false`/unset,
   **When** `Layout` renders,
   **Then** a test asserts no API-docs link is present (query-by-label returns nothing), while the Documentation and GitHub links still render.

   **Given** a backend config endpoint is added (recommended path),
   **When** it is requested unauthenticated,
   **Then** a backend test asserts it returns 200 with `{"api_docs_enabled": <bool>}` mirroring `settings.API_DOCS_ENABLED` (both when the setting is on and off).

5. **The change harness is green.** `pixi run ci` exits 0 (backend + frontend, coverage ≥ threshold, `mkdocs build --strict` where applicable).

## Tasks / Subtasks

- [ ] **Task 1 — Decide + wire the flag mechanism (AC: #3)** — *Recommended: runtime config endpoint.*
  - [ ] **Backend (recommended):** add a public, unauthenticated `GET /api/v1/config/` view returning `{"api_docs_enabled": settings.API_DOCS_ENABLED}` (AllowAny; no auth/CSRF needed for a read-only public flag). Register it in `backend/generate_sbom/users/urls.py` (or a small dedicated `config` include) under the existing `api/v1/` prefix (`backend/config/urls.py`). Keep the payload minimal and forward-compatible (an object, so future flags can be added).
  - [ ] **Frontend:** add `frontend/src/api/config.ts` (a `getAppConfig()` calling `apiRequest<AppConfig>('/config/')` through the existing `src/api/client.ts`, `API_BASE = '/api/v1'`). Surface the value to `Layout` — either fetch it in a small hook/effect in `Layout.tsx`, or fold it into the existing `AuthProvider` bootstrap so it loads once. Default to **false** on fetch failure so a missing/errored config never shows a link to a possibly-404 endpoint.
  - [ ] **Alternative (only if staying purely build-time):** add `ENABLE_API_DOCS` as `VITE_ENABLE_API_DOCS` in `frontend/src/config.ts` (mirroring the Story 11.8 `VITE_REPO_URL`/`VITE_DOCS_URL` pattern), parsed to a boolean. Document the drift/rebuild trade-off (see Dev Notes) — do NOT do both.
- [ ] **Task 2 — Render the API-docs icon-link (AC: #1, #2)**
  - [ ] In `frontend/src/components/Layout.tsx`, add a `DOCS_API_URL` constant (`'/api/docs/'`, ideally in `frontend/src/config.ts` next to `REPO_URL`/`DOCS_URL`, overridable via `VITE_API_DOCS_URL`).
  - [ ] Conditionally render an `<ExternalIconLink href={DOCS_API_URL} label="API docs">` with an API icon (e.g. `ApiIcon` from `@mui/icons-material/Api`) placed immediately before/after the existing Documentation/GitHub `ExternalIconLink`s (outside the auth conditionals, matching 11.8 placement). Render it only when the flag is true.
- [ ] **Task 3 — Tests (AC: #4)**
  - [ ] Extend `frontend/src/components/Layout.test.tsx`: mock the flag source (the `getAppConfig`/AuthProvider value, or the `VITE_ENABLE_API_DOCS` env) → assert link present when true (correct `href`/`target`/`rel`/label, both auth states) and absent when false/unset.
  - [ ] If the config endpoint is added: add a backend test (e.g. `backend/tests/unit/test_app_config.py` or extend an existing users test) asserting the endpoint returns 200 + the correct `api_docs_enabled` value, toggling `API_DOCS_ENABLED` on and off (`override_settings`).
- [ ] **Task 4 — Harness (AC: #5)**
  - [ ] Run `pixi run ci`; fix until green.

## Dev Notes

### The key design decision — how the flag reaches the SPA

Investigated the codebase's existing conventions:

- **Backend gating (Story 11.9):** `/api/docs/`, `/api/schema/`, `/api/redoc/` are registered in `backend/config/urls.py` **only** when `settings.API_DOCS_ENABLED` (env var `API_DOCS_ENABLED`, `base.py` default `True`, `production.py` env-overridable). When disabled, the endpoints return **404**. This is a **runtime** setting.
- **Frontend config-to-SPA:** the **only** established mechanism is **build-time** Vite env (`import.meta.env.VITE_*`) — see `frontend/src/config.ts` (`VITE_REPO_URL`, `VITE_DOCS_URL` from Story 11.8). There are **no `.env` files**, no `vite-env.d.ts`, and **no public runtime config endpoint**. `auth/me` exists but is **authed-only**, and the header links must show in **both** auth states — so it cannot carry this flag.

**Recommendation — runtime config endpoint (chosen path).** Add a tiny public `GET /api/v1/config/` returning `{"api_docs_enabled": settings.API_DOCS_ENABLED}`. Rationale:

- **Single source of truth:** the link is driven by the **same** setting that gates the endpoint (AC #3), so the link and the Swagger UI are always enabled together — the link can never point at a 404.
- **Docker-friendly:** an operator toggles `API_DOCS_ENABLED` once (env var) and **both** the endpoint and the header link change with **no frontend rebuild** — matching how the backend flag already behaves.

**Trade-off — build-time `VITE_ENABLE_API_DOCS` (alternative).** This matches the exact Story 11.8 `config.ts` pattern (smallest diff, no backend change). Downsides: (a) it is **baked at build time**, so toggling requires **rebuilding the frontend image**; and (b) it is a **separate** flag from backend `API_DOCS_ENABLED`, so the two can **drift** — a build with `VITE_ENABLE_API_DOCS=true` served against a backend with `API_DOCS_ENABLED=false` shows a link to a 404. Because of the drift risk and the deploy-toggle requirement, the **runtime endpoint is preferred**; the implementer may still choose the build-time flag if they want to stay purely within the established 11.8 pattern, but must accept the trade-off.

Name the flag consistently with the backend: env `API_DOCS_ENABLED` (already exists), surfaced to the SPA either as `api_docs_enabled` on the config endpoint (recommended) or as `VITE_ENABLE_API_DOCS` (alternative).

### Concrete files to touch

Runtime path (recommended):
- `backend/config/urls.py` — no change if the config view is included via `users.urls`; otherwise add the include.
- `backend/generate_sbom/users/urls.py` + `backend/generate_sbom/users/views.py` — add `AppConfigView` (`AllowAny`) at `config/`.
- `backend/tests/unit/test_app_config.py` (new) — endpoint returns 200 + correct flag, on and off.
- `frontend/src/api/config.ts` (new) — `getAppConfig()`.
- `frontend/src/config.ts` — add `DOCS_API_URL` (`/api/docs/`, `VITE_API_DOCS_URL` override).
- `frontend/src/components/Layout.tsx` — conditional `ExternalIconLink` with an API icon; consume the flag (via `AuthProvider` bootstrap or a small effect).
- `frontend/src/components/Layout.test.tsx` — present-when-true / absent-when-false, both auth states.
- (If folded into bootstrap) `frontend/src/auth/AuthProvider.tsx` — expose `apiDocsEnabled`.

Build-time alternative:
- `frontend/src/config.ts` — add `ENABLE_API_DOCS` from `VITE_ENABLE_API_DOCS` + `DOCS_API_URL`.
- `frontend/src/components/Layout.tsx` + `Layout.test.tsx` — same as above, minus the backend/api files.

### Existing header pattern to reuse (Story 11.8)

`Layout.tsx` already defines `ExternalIconLink({ href, label, children })` (`Tooltip` + `IconButton component="a" target="_blank" rel="noopener noreferrer" aria-label={label}`). The Documentation (`MenuBook`) and GitHub (`GitHub`) links sit after `<Box sx={{ flexGrow: 1 }} />` and before `<ThemeToggle />`, outside the auth conditionals. Add the API-docs link in that same block, conditionally. Icons come from `@mui/icons-material` (already a dependency since 11.8).

### Coordination

- **Story 11.8** owns the existing Documentation + GitHub header links — reuse its `ExternalIconLink` and placement; do not restyle them.
- **Story 11.9** owns the `/api/docs/` endpoint and `API_DOCS_ENABLED`; this story consumes that flag, it does not change the gating.
- **Story 11.19** (schema completeness) — no file overlap; the link simply opens whatever Swagger UI 11.9/11.19 produce.

### Project Structure Notes

- Frontend: React + Vite + MUI; all network calls route through `frontend/src/api/client.ts` (`API_BASE = '/api/v1'`) — never `fetch` directly (AD-5). Tests: Vitest + Testing Library (`*.test.tsx`).
- Backend: DRF under `api/v1/`; a public read-only flag view uses `permission_classes = [AllowAny]`.
- Gate: `pixi run ci` (backend `pytest` + coverage, frontend `vitest` + build).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 11.20]
- Story 11.8: `11-8-repository-and-documentation-header-links.md` (`frontend/src/config.ts`, `frontend/src/components/Layout.tsx`, `ExternalIconLink`)
- Story 11.9: `11-9-openapi-schema-and-swagger-ui-endpoint.md` (`backend/config/urls.py` gating, `API_DOCS_ENABLED`, `backend/config/settings/base.py` + `production.py`)
- Frontend API client: `frontend/src/api/client.ts` (`API_BASE = '/api/v1'`)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
