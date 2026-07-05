# Story 11.8: Repository & Documentation Links in the App Header

Status: review

## Story

As a user,
I want quick links to the source repository and the documentation from the app,
so that I can reach the code and the docs without hunting for URLs.

## Acceptance Criteria

1. The app header (Epic 10 shell) shows two icon links on every page and in both auth
   states: a GitHub icon → source repo, and a documentation icon → published docs site
   (FR-DOC8).
2. Each link opens in a new tab (`target="_blank"` + `rel="noopener noreferrer"`) and
   carries an accessible label/tooltip ("GitHub repository", "Documentation").
3. The repo/docs URLs come from a single config module, not hard-coded inline; the docs
   URL matches the Story 11.1 GitHub Pages site.
4. `@mui/icons-material` (user-approved Epic 12 dep) supplies the icons; the buttons sit
   consistently in the header without disrupting the existing nav, org switcher, theme
   toggle, or logout.
5. A test covers both links rendering with the correct `href`, `target`, and accessible
   label.

## Tasks / Subtasks

- [x] Add `frontend/src/config.ts` exporting `REPO_URL` / `DOCS_URL` (Vite env override + defaults) (AC: #3)
- [x] Add `@mui/icons-material` to `frontend/package.json` + lockfile (AC: #4)
- [x] Render two `ExternalIconLink` icon buttons (GitHub, MenuBook) in the toolbar, always visible, next to the theme toggle (AC: #1, #2, #4)
- [x] Extend `Layout.test.tsx` — links render with correct href/target/rel/label, authed and anon (AC: #5)
- [x] `pixi run ci` green

## Dev Notes

Placed the two links after the toolbar's flex spacer and before `ThemeToggle`, so they
render outside the auth conditionals (visible logged-in and logged-out). URLs are
sourced from `../config` (`REPO_URL`, `DOCS_URL`), each overridable via
`VITE_REPO_URL` / `VITE_DOCS_URL` with the repo + `https://millsks.github.io/django-python-generate-sbom/`
defaults. `import.meta.env` is typed via the existing `vite/client` types. This is the
first use of `@mui/icons-material` (v9, matching `@mui/material`); Epic 12 Story 12.2
builds on it.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- `pixi run ci` exits 0: backend 262 passed (93.90% coverage), frontend 94 passed (19 files), fe-build succeeds.
- The 2 moderate `npm audit` advisories are the pre-existing `exceljs`→`uuid` chain; `fe-security` gates on high/critical so they don't fail CI.
- Pre-existing: `vite build` warns the main JS chunk is >500 kB (code-splitting opportunity) — grew slightly with the icons import; unrelated to this story.

### File List

- `frontend/src/config.ts` (new)
- `frontend/src/components/Layout.tsx`
- `frontend/src/components/Layout.test.tsx`
- `frontend/package.json`
- `frontend/package-lock.json`
