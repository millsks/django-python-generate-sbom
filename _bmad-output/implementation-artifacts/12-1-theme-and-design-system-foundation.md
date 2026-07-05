# Story 12.1: Theme & Design System Foundation

Status: review

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- **Centralized theme** `frontend/src/theme.ts` (was a two-line stub) now builds full light + dark themes from the user-supplied brand palette via `createTheme(sharedOptions, { palette })`. `ThemeModeProvider` already consumed `lightTheme`/`darkTheme`, so the light/dark toggle (Story 5.7) keeps working unchanged.
- **Palette (exact brand hexes):** `primary = #D71E28` (white text, 5.1:1 AA), `secondary = #FFCD41` (dark `#141414` text, ~13:1 — gold always pairs with dark text). Backgrounds/text/dividers from the neutral ramp per the story's mode mapping (light: bg `#F4F0ED`/`#FFFFFF`, text `#141414`; dark: bg `#141414`/`#3B3331`, text `#F4F0ED`). Light secondary text uses `#57514F` (not the lighter `#787070`) to clear AA on the off-white background.
- **Semantic colors:** `error` uses a distinct deeper red `#B00020` so it never reads as the brand primary (per the design note); `warning`/`info` reuse the accent spectrum (orange `#EB691E` / indigo `#5A469B`); `success` introduces a conventional green `#2E7D32` (the brand palette has no green). Dark mode lightens error/info/success for legibility on dark surfaces.
- **Reusable tokens:** exported `brand` (red/gold/goldTints/neutral ramp) and `accentSpectrum` (the 6 warm→cool tones) for future charts / severity / categorical scales (Epic 12.4, data-viz).
- **Typography:** dependency-free system font stack, weighted heading scale, `caption`; buttons are **not** upper-cased (`textTransform: none`).
- **Shape/spacing:** `borderRadius: 8`; default 8px spacing retained.
- **Component defaults** via `theme.components`: `MuiButton` (no elevation, rounded), `MuiCard` (rounded), `MuiAppBar` (flat + divider border), `MuiChip`, `MuiTextField`/`MuiTable` (size small) — so pages don't restyle ad-hoc.
- **Accessibility:** a global `*:focus-visible` outline (brand red, 2px) gives every interactive element a visible keyboard focus ring (WCAG 2.4.7); palette pairs chosen for AA and documented in the file header.
- **Token migration:** scoped deliberately narrow per the story — components already use MUI semantic colors (`color="primary"` etc.), so they pick up the brand automatically. Left `DepGraph.tsx`'s cytoscape colors and `excelExport.ts`'s spreadsheet color untouched (out of scope / higher risk; belong to 12.4 and the Excel path). No `Layout.tsx` restructure (Story 12.3), no icons (12.2), no `index.html`/favicon (12.5/12.6).
- **Tests:** `frontend/src/theme.test.ts` — primary/secondary map to the brand in both modes, error stays distinct from primary, backgrounds/text derive from the ramp per mode, the accent spectrum is exposed, and shared tokens (rounded shape, non-uppercase buttons) apply. All 20 frontend test files (99 tests) pass — no regressions.
- Gate: `pixi run ci` exits 0.

### File List

- frontend/src/theme.ts (brand palette, light/dark themes, typography, component defaults, exported tokens)
- frontend/src/theme.test.ts (new)

## Story

As a user, I want the app to have a deliberate, consistent visual style, so that it feels like a polished professional product rather than default components. See Epic 12, Story 12.1 (incl. the Brand Palette source-of-truth) in `_bmad-output/planning-artifacts/epics.md`.
