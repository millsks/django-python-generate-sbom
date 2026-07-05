# Story 12.5: Branding & Visual Identity

Status: review

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Added a cohesive **header brand mark** to `Layout.tsx`: a lockup of the Material
  `Inventory2` icon (bill-of-materials mark) + the `APP_NAME` wordmark, wrapped in the
  existing home link (`RouterLink to="/"`). The wordmark uses a bold, slightly
  letter-spaced treatment; the whole lockup keeps its accessible name "Generate SBOM".
- **Color decision:** the app bar is `colorPrimary` → brand red `#D71E28` background with
  white content (theme 12.1). A brand-red icon would be invisible red-on-red, so the mark
  renders in `inherit` (white) — the **brand red is carried by the app-bar background**,
  and the shared **Inventory2 shape** is what makes the app mark match the favicon
  (Story 12.7 renders the same icon in brand red on a light background). App + favicon
  share the mark; color adapts to context.
- Colors come from the 12.1 theme tokens (no hard-coded values); the mark shows in both
  authed and logged-out states for a consistent identity.
- Imported `Inventory2Icon` directly in `Layout.tsx`, consistent with the file's existing
  direct icon imports (GitHub/MenuBook/Menu) — no change to the shared `icons.ts` (12.2).
- Scope kept to header branding: did not touch `index.html`/favicon (12.7), `theme.ts`
  (12.1), page components (12.4), or backend.

### File List

- `frontend/src/components/Layout.tsx` — header brand-mark lockup (Inventory2 + wordmark)
- `frontend/src/components/Layout.test.tsx` — 2 tests: brand mark links home with the
  Inventory2 icon (authed), and the mark shows when logged out

### Change Log

- feat(ui): add header brand mark (Inventory2 + wordmark) for a cohesive identity (Story 12.5)
