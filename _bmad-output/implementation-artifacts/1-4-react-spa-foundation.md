# Story 1.4: React SPA Foundation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a React SPA foundation wired into Django's static serving,
so that all frontend features can be built on a consistent stack and served correctly in both dev and production.

## Acceptance Criteria

1. Given the `frontend/` directory at the project root (AD-13), when I run `npm install && npm run build` from `frontend/`, then `frontend/dist/` is populated with built assets (at minimum `index.html` and a JS bundle) and the command exits 0.
2. Given `collectstatic` has run in the `backend/` environment, when I send `GET /` to the Django web server, then Django serves `frontend/dist/index.html` via WhiteNoise with a `200` response.
3. Given the React app loaded in a browser, when I navigate to any path not handled by the Django URL router (e.g., `/dashboard`), then Django returns the SPA `index.html` (catch-all URL pattern) and React Router handles the route client-side — no Django 404.
4. Given `backend/config/settings/base.py`, when I inspect `STATICFILES_DIRS`, then it contains `BASE_DIR.parent.parent / 'frontend' / 'dist'` (resolves to `frontend/dist/` relative to the project root, per AD-5).
5. Given `frontend/src/api/`, when a developer needs to call a REST API endpoint, then the call is made via a function in `frontend/src/api/` — no direct `fetch` or `axios` calls appear in component files (AD-5).
6. Given `frontend/vite.config.ts`, when `npm run build` executes, then the output directory is set to `../dist` (relative to `frontend/src`) resolving to `frontend/dist/` — matching what Django's `STATICFILES_DIRS` references.
7. Given the pixi umbrella (amended AD-13), when `pixi run ci` runs from the project root, then it invokes the frontend lint + build steps (via pixi tasks with `cwd = "frontend"` shelling to npm/vite) in addition to the backend steps — pixi provides the Node runtime; npm still manages JS dependencies. (This REVERSES the original "pixi run ci must never invoke npm" wording — pixi is now the whole-project umbrella. See memory pixi-umbrella-toolchain.)

## Tasks / Subtasks

- [ ] Task 1 — Scaffold the Vite + React + TS app under `frontend/` (AC: #1)
  - [ ] `npm create vite@latest` with the React + TypeScript template inside `frontend/` (Vite 8.1.3, React 19.2.7)
  - [ ] Add `@mui/material` 9.1.2 and its peer deps (`@emotion/react`, `@emotion/styled`)
  - [ ] Add `react-router-dom` for client-side routing
  - [ ] Add graph deps for later stories now so the toolchain is complete: `cytoscape` 3.34.0, `react-cytoscapejs` 2.0.0, `cytoscape-dagre` 4.0.0 (not used yet; import only in Epic 5)
  - [ ] `npm install && npm run build` exits 0 and populates `dist/`
- [ ] Task 2 — Configure Vite build output (AC: #4, #6)
  - [ ] `vite.config.ts` `build.outDir` resolves to `frontend/dist/` (i.e. `../dist` from `src`, or `dist` from `frontend/` root depending on root config) so it matches Django's `STATICFILES_DIRS`
  - [ ] Set correct `base` so asset URLs resolve under WhiteNoise's static serving
- [ ] Task 3 — API client module (AC: #5)
  - [ ] Create `frontend/src/api/client.ts`: base client that injects the `Authorization` header and centralizes `fetch`
  - [ ] Establish the rule (and a placeholder for the shared `useJobStatus(taskId)` hook, implemented in Epic 6) that ALL network calls route through `src/api/` — no `fetch`/`axios` in components (AD-5)
  - [ ] Stub the domain modules referenced by the design so later stories drop in: `jobs.ts`, `reports.ts`, `keys.ts`, `orgs.ts` (empty typed stubs are fine)
- [ ] Task 4 — Router + placeholder home page (AC: #3)
  - [ ] Set up `react-router-dom` with a browser-history router and a placeholder home route
  - [ ] Confirm client-side routes work when served from a deep path (relies on the Django catch-all in Task 6)
- [ ] Task 5 — Django static serving wiring (AC: #2, #4)
  - [ ] In `backend/config/settings/base.py`: `STATICFILES_DIRS = [BASE_DIR.parent.parent / 'frontend' / 'dist']`
  - [ ] Ensure WhiteNoise middleware is enabled (added in Story 1.3) and `STATIC_ROOT` / `STATIC_URL` configured for `collectstatic`
  - [ ] Serve `index.html` at `/` via WhiteNoise (or a small `SpaView`)
- [ ] Task 6 — SPA catch-all URL (AC: #3)
  - [ ] In `backend/config/urls.py`, add the catch-all AFTER `api/` and `health/` routes: `re_path(r'^(?!api/|health/|static/).*$', SpaView.as_view())` serving `index.html`
  - [ ] Verify `/api/...` and `/health/` are NOT shadowed by the catch-all
- [ ] Task 7 — Verify toolchain independence (AC: #7)
  - [ ] Confirm `pixi run ci` (from `backend/`) invokes no npm/frontend commands
  - [ ] Confirm the frontend has its own `package.json` scripts (`dev`, `build`, `lint`) run from `frontend/`
- [ ] Task 8 — Verification (AC: #1, #2, #3)
  - [ ] Build the SPA, run `collectstatic`, hit `/` → 200 serving `index.html`
  - [ ] Hit a deep client route (e.g. `/dashboard`) → 200 serving `index.html` (React Router takes over)
  - [ ] Backend `pixi run ci` still exits 0 (any new backend view/test included)

## Dev Notes

### Frontend stack (ARCHITECTURE-SPINE.md § Stack; solution-design.md § 7.1)

| Library | Version | Role |
|---|---|---|
| React | 19.2.7 | SPA framework |
| @mui/material | 9.1.2 | Component library |
| Vite | 8.1.3 | Build tool |
| cytoscape | 3.34.0 | Graph engine (used in Epic 5) |
| react-cytoscapejs | 2.0.0 | React wrapper (Epic 5) |
| cytoscape-dagre | 4.0.0 | Hierarchical layout (Epic 5) |
| react-router-dom | current | Client-side routing |

Install the cytoscape trio now so the toolchain is settled, but do not build the graph panel — that's Epic 5 Story 5.5 (`DepGraph.tsx`).

### Static serving flow (AD-5, AD-13; solution-design.md § 7.4)

Vite builds to `frontend/dist/` at the project root. `STATICFILES_DIRS = [BASE_DIR.parent.parent / 'frontend' / 'dist']` (note the double `.parent`: from `backend/config/settings/base.py`, `BASE_DIR` is `backend/`, `.parent` is the project root, `.parent.parent`… — verify `BASE_DIR` definition and adjust the number of `.parent` calls so the path resolves to `<project-root>/frontend/dist`). `collectstatic` copies assets into `STATIC_ROOT`; WhiteNoise serves them. The Django SPA catch-all (`re_path(r'^(?!api/|health/).*$', SpaView.as_view())`) serves `index.html` for all non-API routes, enabling React Router browser-history mode.

CRITICAL path check: confirm what `BASE_DIR` points at in the generated settings (cookiecutter-django sometimes sets it to the project package dir, sometimes to `backend/`). The invariant is that `STATICFILES_DIRS[0]` must equal `<project-root>/frontend/dist`. Adjust `.parent` depth to match the actual `BASE_DIR`, and add an assertion/test if practical.

### API layer convention (AD-5; solution-design.md § 7)

All REST calls live in `frontend/src/api/` — never `fetch`/`axios` directly in components. Modules mirror the API surface: `client.ts` (base + auth header), `jobs.ts`, `reports.ts`, `keys.ts`, `orgs.ts`. The shared `useJobStatus(taskId)` polling hook is defined in Epic 6 but the `src/api/` seam is established here. Frontend state-management library (React Query vs Zustand vs Redux) is deferred to story implementation — the only binding constraint is the `src/api/` convention (spine Deferred; solution-design § 12).

### In Docker (from Story 1.2)

The `frontend-build` compose service runs `npm ci && npm run build` into the shared `frontend-dist` volume; `web` mounts it read-only at `/app/frontend/dist` so `collectstatic` sees the assets. This story makes the local `npm run build` + Django serving work; the compose plumbing already exists from Story 1.2.

### Testing standards

- Frontend: a minimal build smoke test is sufficient here (build exits 0, `dist/index.html` exists). Component testing infra can be added with the first real component in Epic 5.
- Backend: the `SpaView` / catch-all deserves a unit test — `/` and a deep route return 200 serving `index.html`; `/api/...` and `/health/` are not shadowed. This test counts toward the backend ≥90% gate.

### Constraints / guardrails

- AD-13: frontend toolchain is fully independent of the backend pixi toolchain. `pixi run ci` must never invoke npm (AC #7). Frontend lint/build run from `frontend/` via `package.json` scripts.
- Do not introduce SSR or Django template rendering of business data (AD-5) — the SPA talks only to `/api/v1/`.
- No PyVis, no iframes for any future graph work (AD-9) — the cytoscape deps installed here are the sanctioned path.

### Project Structure Notes

- `frontend/` is a project-root peer to `backend/` (AD-13) with its own `package.json`, `vite.config.ts`, `src/`, and build output `dist/`.
- `frontend/dist/` is a build artifact — confirm it is gitignored (add `frontend/dist/` to `.gitignore` if not already covered).
- The catch-all URL is the last pattern in `config/urls.py`; ordering matters — `api/` and `health/` must precede it.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4: React SPA Foundation]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA: REST API only]
- [Source: ARCHITECTURE-SPINE.md#AD-13 — Monorepo layout]
- [Source: ARCHITECTURE-SPINE.md#Stack]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Frontend data]
- [Source: solution-design.md#7. Frontend Architecture]
- [Source: solution-design.md#7.4 Static serving]
- [Source: solution-design.md#2. Repository Layout — frontend/]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
