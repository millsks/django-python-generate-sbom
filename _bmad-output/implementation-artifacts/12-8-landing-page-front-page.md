# Story 12.8: Landing Page (App Home)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a visitor,
I want the home page to explain what the app does and how to start,
so that I understand the product and can jump straight into generating an SBOM.

## Acceptance Criteria

1. **Hero + CTAs.** `HomePage` (`/`, public, in the app shell) shows the app name (`APP_NAME`), a headline + short supporting line, a primary CTA **"Upload a manifest"** → `/upload` (anon → login via `ProtectedRoute`), and a secondary **"Read the docs"** → `DOCS_URL`.
2. **Feature grid + how-it-works.** A responsive "What you get" grid presents the real features (SBOM document, vulnerability report, license compliance, dependency graph, version currency, Excel export) with the `TabIcon`/action-icon vocabulary; a "How it works" section shows upload → resolve/analyze → review → export.
3. **Design-system compliant.** MUI theme components + palette only (no hard-coded colors); light/dark aware; responsive to mobile.
4. **Tested; CI green.** A test asserts the headline, the `/upload` CTA, the docs link, and the feature tiles. `pixi run ci` green.

## Tasks / Subtasks

- [x] Replace the placeholder `frontend/src/pages/HomePage.tsx` with hero (name/headline/CTAs), a `Box` CSS-grid feature section (MUI v9 — avoid the Grid API churn), and a how-it-works section; reuse `APP_NAME`/`DOCS_URL` (`config.ts`) and `TabIcon`/`ExportIcon`/`UploadActionIcon` (`icons.ts`).
- [x] Add `frontend/src/pages/HomePage.test.tsx` (Vitest + RTL, `MemoryRouter`): headline, `/upload` CTA href, docs link href, feature/how-it-works headings.
- [x] `pixi run ci` green.

## Dev Notes

- `/` is public (`App.tsx:22`, not under `ProtectedRoute`) and renders inside `Layout`, so the page appears for anonymous visitors too; the "Upload a manifest" CTA points at a protected route and `ProtectedRoute` handles the login redirect.
- Feature set verified against `icons.ts` `TabIcon` (overview/sbom/vulnerabilities/licenses/graph/versions) + `ExportIcon`, matching the shipped report tabs and Excel export.
- MUI is `^9.1.2`; used `Box` with `display:'grid'` + responsive `gridTemplateColumns` instead of `Grid` for version-safety. Palette colors (`color="primary"`, `text.secondary`) keep it light/dark aware.

### References

- `frontend/src/pages/HomePage.tsx`, `frontend/src/config.ts` (`APP_NAME`, `DOCS_URL`), `frontend/src/icons.ts`, `frontend/src/App.tsx:22`
- Related: Story 12.1 (design system), 12.3 (app shell), 12.5 (branding)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (1M context)

### Completion Notes List

- Implemented the landing page + test; full `pixi run ci` green.

### File List

- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/HomePage.test.tsx`
