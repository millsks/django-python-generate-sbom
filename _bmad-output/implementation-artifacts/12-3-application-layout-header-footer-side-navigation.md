# Story 12.3: Application Layout — Header, Footer & Side Navigation

Status: review

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Refined the Epic 10 shell (`Layout.tsx`) into a professional layout on the 12.1 theme,
  without touching routing/auth behavior:
  - **Header:** fixed `AppBar` (z-index above the drawer) with the `APP_NAME` brand
    (home link), the org switcher, theme toggle, repo/docs icon links (Story 11.8),
    and the account menu (Logout) — all preserved. A hamburger (`MenuIcon`) appears
    only on small screens to open the temporary drawer.
  - **Side navigation:** new `SideNav.tsx` — the primary destinations (Upload / History /
    API Keys, + Members for admins) as a `nav` landmark with `NavLink` active
    indication, plus a contextual side region showing the active org. Rendered in a
    **permanent** `Drawer` on desktop and a **temporary** (hamburger-toggled) `Drawer`
    on small screens, chosen via `useMediaQuery(theme.breakpoints.down('md'))`.
  - **Main region:** `<Outlet/>` in a `component="main"` box with a `Toolbar` spacer
    under the fixed app bar.
  - **Footer:** new `Footer.tsx` — `APP_NAME` + version and Docs / GitHub / License
    links (reusing `REPO_URL`/`DOCS_URL`); shown across all pages and auth states.
- Anonymous users get no side drawer; the header shows Login / Register (unchanged).
- Icon use kept minimal/structural (hamburger only) — broad icon adoption is Story 12.2.
- Added `APP_VERSION` to `config.ts` (mirrors `package.json`) for the footer.

### File List

- `frontend/src/components/Layout.tsx` (refined)
- `frontend/src/components/SideNav.tsx` (new)
- `frontend/src/components/Footer.tsx` (new)
- `frontend/src/config.ts` (added `APP_VERSION`)
- `frontend/src/components/Layout.test.tsx` (updated: nav-in-drawer, responsive
  hamburger/drawer, footer, contextual side info; existing behaviors retained)
