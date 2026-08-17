# Story 21.18: Landing Page and Visual Identity

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.17**. The last page to convert, and the one carrying Epic 12's branding
> work. **After this story every route has a Django owner**, which is what unblocks Story 21.19.

> **Note:** **No UX design contract exists for this project** (`epics.md:13`). Parity is judged against the
> currently rendered SPA, not against a design spec — hence the product-owner review in AC #5.

## Story

As a visitor,
I want a landing page that explains the product,
so that I understand what the service does before signing in.

## Acceptance Criteria

1. **Both landing states are converted.**
   Given `HomePage.tsx` renders a feature-card landing page for anonymous visitors and an authenticated entry
   point for signed-in users (Story 12.8), when it is converted, then both states render at `/`, with the same
   feature cards, the same primary calls to action, and the documentation link preserved.
2. **The visual identity carries over under the new name.**
   Given Epic 12 established a theme, icon set, and branding (Stories 12.1, 12.2, 12.5, 12.6, 12.7), when the
   identity is carried over, then the header brand shows the short form **"Supply Lens"**, the landing page
   `<title>` uses the full **"Python Inventory Supply Lens"**, per-page document titles are preserved in form,
   the favicon (Story 12.7) is carried over, and Bootstrap Icons equivalents of the MUI icons are used
   consistently across nav, tabs, and actions.
3. **The layout is responsive.**
   Given the SPA is responsive, when the templates render on a narrow viewport, then navigation collapses and
   the wide report tables scroll **within their own container** rather than forcing the page to scroll
   horizontally.
4. **A signed-in user with no org still lands somewhere useful.**
   Given Story 2.18 restricts zero-org users to the home page, when such a user lands on `/`, then they see
   the zero-org state from Story 21.4 rather than an empty dashboard or an error.
5. **Visual parity is reviewed, not assumed.**
   Given parity here is subjective and no UX contract exists, when the story completes, then the two page
   states, the document titles, and the favicon are covered by tests, **the product owner reviews the rendered
   result side by side against the current SPA**, and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] **Task 1 — Landing page, both states (AC: #1, #4)**.
- [ ] **Task 2 — Branding + titles + favicon (AC: #2)** — Using the two name forms defined in Story 21.3.
- [ ] **Task 3 — Icon mapping (AC: #2)** — MUI → Bootstrap Icons across nav, tabs, and actions; one mapping
  module, not per-template literals.
- [ ] **Task 4 — Responsive pass (AC: #3)** — Collapsing nav; `overflow-x: auto` containers for wide tables.
- [ ] **Task 5 — Review + gate (AC: #5)** — Side-by-side product-owner review; record the outcome.

## Dev Notes

### Grounded facts (verified)

- `frontend/src/pages/HomePage.tsx` — imports `APP_NAME` and `DOCS_URL` from `config.ts`, branches on
  `useAuth()`, renders feature cards, and falls back to `NoOrgState`.
- `frontend/src/config.ts` — `APP_NAME` (Story 12.6, "the single source for the browser document title and the
  header brand, so the name isn't duplicated as a string"), `APP_VERSION` (shown in the footer, Story 12.3),
  `REPO_URL` and `DOCS_URL` (Story 11.8, overridable via Vite env vars), `DOCS_API_URL` (Story 11.20).
- `frontend/src/icons.ts` — the centralised icon mapping (`NavIcon`, `TabIcon`, `currencyIcon`,
  `ExportIcon`, …) introduced by Story 12.2. Mirror this centralisation; do not scatter icon names.
- Epic 12 stories in scope: 12.1 (theme/design tokens), 12.2 (Material icons adoption), 12.3 (layout: header,
  footer, side nav), 12.4 (page-level visual polish and states), 12.5 (branding), 12.6 (SPA document title),
  12.7 (favicon), 12.8 (landing page).
- `App.tsx` routes `*` to `HomePage`, so the landing page is also the catch-all fallback.

### `REPO_URL` / `DOCS_URL` were build-time overridable

They come from Vite env vars with defaults. The Django equivalent should be settings-driven with the same
defaults so deployments can still override them without a rebuild.

### Icons: keep the indirection

Story 12.2 centralised icons in `icons.ts` precisely so a swap like this one is a single-file change. Recreate
that indirection server-side (a template tag or a mapping module) rather than embedding `bi-*` class names in
twenty templates.

### Watch for

- **The `*` route fallback.** `App.tsx` sends unknown paths to `HomePage`. Decide deliberately whether the
  Django app 404s instead — a real 404 is better behaviour, but it **is** a behaviour change; flag it in the
  review rather than shipping it silently.
- **`APP_VERSION` in the footer** mirrors `package.json`. Once `frontend/` is gone it must come from the Python
  distribution version instead.

### Testing standards

- Tests for the anonymous state, the authenticated state, the zero-org state, document titles, and the favicon
  reference.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.18: Landing Page and Visual Identity]
- `frontend/src/pages/HomePage.tsx`, `frontend/src/config.ts`, `frontend/src/icons.ts`,
  `frontend/src/theme.ts`, `frontend/index.html`, `frontend/public/`.
- Upstream: `21-17-server-side-excel-export.md`. Downstream: `21-19` (**every route must have a Django owner
  before it can run**).

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
