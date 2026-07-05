# Story 12.6: Set the SPA Document Title

Status: review

## Story

As a user,
I want the browser tab to show the product name,
so that the app is identifiable among my open tabs instead of reading "frontend".

## Acceptance Criteria

1. The base document title (`frontend/index.html`) is the product name, replacing the
   Vite placeholder `frontend`, so a freshly loaded page shows it in the browser tab
   (FR-UI7).
2. Per-route titles are optionally supported (`<page> · <App>`) while always falling
   back to the product name; the base title fix is the required part.
3. The title matches the app name used for the header brand, sourced from the
   `config.ts` app-identity constant rather than a second hard-coded name string.

## Tasks / Subtasks

- [x] Set `frontend/index.html` `<title>` to "Generate SBOM" (AC: #1)
- [x] Add `APP_NAME` to `frontend/src/config.ts` as the single source (matches the
      `Layout.tsx` header brand "Generate SBOM") (AC: #3)
- [x] Add a minimal `useDocumentTitle(page?)` hook that sets `document.title` to
      `<page> · APP_NAME` (or `APP_NAME`) for pages to adopt (AC: #2)
- [x] Test the hook + the app-name constant (AC: #1, #2)

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes

- Chose product name **"Generate SBOM"** to match the existing header brand in
  `Layout.tsx` (line 76); the README repo name (`django-python-generate-sbom`) is the
  slug, not the display name.
- `APP_NAME` lives in the existing `config.ts` alongside `REPO_URL`/`DOCS_URL` so Story
  12.5 branding and the header can reuse the one constant.
- The `useDocumentTitle` hook is provided + unit-tested but intentionally NOT wired into
  page components or `App.tsx` — that would touch files Stories 12.3 (layout) / 12.4
  (page polish) own, risking merge conflicts with sibling Epic-12 work. The required
  base-title fix (index.html) stands alone; pages can adopt the hook later.
- `pixi run ci` green.

### File List

- `frontend/index.html` (title)
- `frontend/src/config.ts` (`APP_NAME`)
- `frontend/src/hooks/useDocumentTitle.ts` (new)
- `frontend/src/hooks/useDocumentTitle.test.ts` (new)
