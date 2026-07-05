# Story 12.7: Update the Site Favicon

Status: review

## Story

As a user, I want the browser tab to show a real favicon, so that the app is
recognizable and looks finished, not a scaffold default.

## Acceptance Criteria

See Epic 12, Story 12.7 in `_bmad-output/planning-artifacts/epics.md` (FR-UI8).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes

- Replaced the Vite placeholder `frontend/public/favicon.svg` (purple lightning mark,
  `#863bff`) with a deliberate favicon derived from the **Material Design `Inventory2`**
  icon (bill of materials — apt for an SBOM tool). Material icons are Apache-2.0
  licensed, so there is no trademark concern (unlike the Python logo). Same icon used
  for the app brand in Story 12.5, keeping the identity consistent.
- The exact `Inventory2` path was taken from the installed `@mui/icons-material`
  package and colored with the brand red `#D71E28` (Story 12.1 palette) on a
  transparent background, 24×24 viewBox.
- `frontend/index.html` already links `<link rel="icon" type="image/svg+xml"
  href="/favicon.svg" />`, so replacing the asset is sufficient; left the link in place.
- Added `frontend/src/favicon.test.ts` asserting the favicon is the brand-colored
  Material SVG (not the Vite default) and that `index.html` references it.

### File List

- `frontend/public/favicon.svg` (replaced)
- `frontend/src/favicon.test.ts` (new)
- `_bmad-output/implementation-artifacts/12-7-update-the-site-favicon.md` (new)
