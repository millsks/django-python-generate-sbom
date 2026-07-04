# Story 5.7: Light/Dark Theme Toggle (app-wide)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to switch the interface between light and dark themes,
so that I can read the UI comfortably instead of being stuck on a hard-to-read default.

## Context / root cause

The SPA currently has **no MUI `ThemeProvider`**, so components fall back to MUI's
default palette while Vite's generated `index.css` sets a dark `color-scheme` —
the mismatch makes form fields and text hard to see. This story adds a proper
theme with a user-controlled light/dark toggle. App-wide (affects every page:
login, register, dashboard, members, keys, upload, and the future results/history
views). Can be pulled forward ahead of Epic 5 since it affects pages already built.

## Acceptance Criteria

1. Given the app loads, when no preference is stored, then it follows the OS `prefers-color-scheme`; a MUI `ThemeProvider` + `CssBaseline` apply the palette consistently so all fields and text are legible in both modes.
2. Given a theme toggle control in the app chrome, when I switch light↔dark, then the whole UI updates immediately and every page (login/register/dashboard/members/keys/upload) is legible in the chosen mode.
3. Given I have chosen a theme, when I reload or navigate, then my choice persists (e.g. `localStorage`) and is reapplied on load.
4. Given the toggle, when the page first paints, then there is no jarring flash of the wrong theme (apply the stored/system preference before first meaningful paint).
5. Given the vite-default `index.css`, when the theme is applied, then hardcoded colors that fight the MUI palette are removed/neutralized so `CssBaseline` governs background/text.

## Tasks / Subtasks

- [ ] Task 1 — Theme setup
  - [ ] Add a MUI `createTheme` light + dark palette; wrap the app in `ThemeProvider` + `CssBaseline`
  - [ ] Remove/neutralize the vite-default dark colors in `index.css` so `CssBaseline` owns background/text
- [ ] Task 2 — Toggle + persistence
  - [ ] A theme toggle (icon button) in the app chrome; mode state in a small context/provider
  - [ ] Default to `prefers-color-scheme`; persist the user's choice in `localStorage`; reapply on load (no wrong-theme flash)
- [ ] Task 3 — Verify legibility across pages
  - [ ] Check login, register, dashboard, members, keys, upload in both modes
- [ ] Task 4 — Gate
  - [ ] Frontend lints (oxlint) and builds (tsc + vite); `pixi run ci` exits 0

## Dev Notes

- Frontend-only; lives in `frontend/src/` (a `theme.ts`, a small `ThemeModeProvider`, and the toggle component). API layer unchanged (AD-5).
- No backend changes; no persistence server-side (localStorage is sufficient for v1).
- Keep it minimal: MUI's `ThemeProvider` + `CssBaseline` + a `useMediaQuery('(prefers-color-scheme: dark)')` default + a `localStorage`-backed override.

### References

- [Source: Kevin request (2026-07-03) — UI is stuck dark / fields barely visible]
- [Source: ARCHITECTURE-SPINE.md#AD-5 — React SPA]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
