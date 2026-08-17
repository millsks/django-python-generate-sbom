# Story 21.3: Server-Rendered UI Foundation

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.2**. Every page story from 21.5 onward depends on the base template,
> the asset pipeline, and the crispy configuration this story establishes. No business page is converted here.

> **⚠ SIGN-OFF GATE.** This story proposes **five new dependencies**: `django-crispy-forms`,
> `crispy-bootstrap5`, `django-tables2`, `django-filter` (conda-forge first), plus a **vendored** htmx asset.
> Propose; do not add until explicitly approved (Control Constraints §7).

## Story

As a developer,
I want a base template, CSS framework, form renderer, and htmx wired into the project,
so that every subsequent page story writes only its own template and view instead of re-solving layout,
styling, and asset delivery.

## Acceptance Criteria

1. **The UI dependencies are proposed and configured.**
   Given the project has no UI dependencies today, when the foundation lands, then the story **proposes**
   `django-crispy-forms`, `crispy-bootstrap5`, `django-tables2`, and `django-filter` (conda-forge first per the
   toolchain standard) plus a vendored htmx asset, adds them only after explicit approval, and configures
   `CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"` and `CRISPY_TEMPLATE_PACK = "bootstrap5"`.
2. **Two template roots, matching the reference application.**
   Given `TEMPLATES` currently has `DIRS: []` and `APP_DIRS: True` (`base.py:94-107`), when templates are
   added, then `DIRS` becomes `[APPS_DIR / "templates"]` holding the **project shell** (`base.html` plus
   `403.html`, `403_csrf.html`, `404.html`, `500.html`), `APP_DIRS: True` is retained so
   `src/django_apps/inventory/templates/inventory/` resolves for app pages, project-wide static lives at
   `APPS_DIR / "static"` via `STATICFILES_DIRS`, and app static lives at
   `src/django_apps/inventory/static/inventory/`.
3. **All assets are served locally, with no CDN.**
   Given the project already self-hosts its OpenAPI assets via `drf-spectacular-sidecar`, when Bootstrap 5.3,
   Bootstrap Icons, and htmx are added, then all three are served from local static and **no external CDN
   reference exists** in any template.
4. **The product name is defined once, in two forms.**
   Given `frontend/src/config.ts:3` defines `APP_NAME = 'Generate SBOM'` as the single source for the document
   title and header brand (Story 12.6), when the name is carried over, then a single Django-side definition
   provides the **full name "Python Inventory Supply Lens"** and the **short form "Supply Lens"**, both
   exposed to templates via a context processor or template tag, with **no literal duplication** of either
   string in any template.
5. **The app shell reproduces the SPA layout.**
   Given `Layout.tsx` and `SideNav.tsx` render a header, footer, and seven role-gated nav items
   (`SideNav.tsx:44-51`), when `base.html` is written, then it provides the same header (branded with the short
   form), footer, and side navigation — Home, Upload, History, Members (admin), API Keys, Organization
   (admin), Global Admins (global admin) — with the same role gating, a `{% block title %}` reproducing the
   per-page document titles, and the Django `messages` framework rendered as dismissible alerts.
6. **The theme toggle survives.**
   Given `ThemeModeProvider.tsx` persists a `light`/`dark` choice under the `theme-mode` localStorage key and
   falls back to the OS preference, when the toggle is reimplemented, then it drives Bootstrap 5.3
   `data-bs-theme`, honours `prefers-color-scheme` when unset, persists under the **same** `theme-mode` key,
   and applies with **no flash of unstyled content** on first paint.
7. **Gate green without colliding with the SPA.**
   Given the SPA catch-all at `backend/config/urls.py:38` still owns every non-API path, when the story
   completes, then the shell is reachable at a temporary route that does not collide with it, unit tests cover
   the nav role gating and the theme default, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 0 — Propose dependencies (AC: #1)** — Present the five adds with rationale; wait for approval.
- [ ] **Task 1 — Settings wiring (AC: #1, #2)** — `INSTALLED_APPS` entries for crispy/tables2/filter,
  `TEMPLATES["DIRS"]`, `STATICFILES_DIRS`, crispy template-pack settings.
- [ ] **Task 2 — Vendor the assets (AC: #3)** — Bootstrap 5.3 CSS/JS, Bootstrap Icons, htmx into
  `APPS_DIR / "static"`. Verify no CDN URL remains.
- [ ] **Task 3 — Product name definition (AC: #4)** — One definition, two forms, exposed to templates.
- [ ] **Task 4 — `base.html` + error templates (AC: #2, #5)** — Header, footer, side nav with role gating,
  `{% block title %}`, messages rendering; `403/403_csrf/404/500`.
- [ ] **Task 5 — Theme toggle (AC: #6)** — `data-bs-theme`, `prefers-color-scheme` fallback, `theme-mode`
  persistence, inline head script to avoid FOUC.
- [ ] **Task 6 — Temporary route + tests + gate (AC: #7)** — Mount the shell somewhere the catch-all does not
  shadow; test nav gating and theme default; `pixi run ci` to green.

## Dev Notes

### Grounded facts (verified)

- `backend/config/settings/base.py:94-107` — `TEMPLATES` with `DIRS: []`, `APP_DIRS: True`, and the
  `request`/`auth`/`messages` context processors **already present**.
- `base.py:83` — WhiteNoise already in `MIDDLEWARE`; `:128-129` — `STATIC_URL`/`STATIC_ROOT` already set;
  `:140` — `CompressedStaticFilesStorage`.
- `frontend/src/components/SideNav.tsx:44-51` — the seven nav items and their role gates (`isAdmin` for
  Members and Organization; global-admin for Global Admins).
- `frontend/src/ThemeModeProvider.tsx` — `STORAGE_KEY = 'theme-mode'`, `light`/`dark`, `useMediaQuery`
  fallback to OS preference.
- `frontend/src/config.ts:3` — `APP_NAME = 'Generate SBOM'`, deliberately a single source (Story 12.6).
- Precedent for local asset hosting: `drf-spectacular-sidecar` is already used specifically so the API docs
  need no CDN (`base.py:60-63`).

### Reference application

`django-15-factor-base` puts the project shell at `src/django_service/templates/` (`base.html`, `403.html`,
`403_csrf.html`, `404.html`, `500.html`, `pages/`) and project static at `src/django_service/static/`
(`css/`, `js/`, `images/`, `fonts/`), wired by `APPS_DIR` at `src/config/settings/base.py:20`, `:224`, `:246`.
This story mirrors that arrangement.

### Design decisions

- **Two template roots, not one.** The project shell belongs to `django_service` (it is host chrome); page
  templates belong to the app. Keeping them separate is what makes the app's templates portable later, and it
  costs nothing now.
- **htmx is vendored, not CDN-loaded**, matching the sidecar precedent and keeping the app functional in
  air-gapped/OpenShift deployments (Epic 19).
- **No navigation registry.** Reference AD-8 would make navigation contributed *data*; pluggability is
  deferred (see the Epic 21 preamble), so the nav is ordinary template markup in this story.

### Testing standards

- Unit tests for nav role gating across anonymous / member / org-admin / global-admin.
- A test asserting the theme default resolves from `prefers-color-scheme` when no `theme-mode` value is set.
- A test asserting no template contains an `http(s)://` asset reference.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.3: Server-Rendered UI Foundation]
- `backend/config/settings/base.py` (L83, L94-107, L128-129, L140), `frontend/src/components/Layout.tsx`,
  `SideNav.tsx`, `ThemeModeProvider.tsx`, `theme.ts`, `config.ts`, `icons.ts`.
- Upstream: `21-2-collapse-apps-into-inventory-and-establish-django-service.md`.
- Downstream: every page story 21.4–21.18.

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Sign-Off Record

_(dependency gate — record approval of the five adds here before starting)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
