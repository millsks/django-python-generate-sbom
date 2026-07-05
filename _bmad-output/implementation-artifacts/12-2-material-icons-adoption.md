# Story 12.2: Material Icons Adoption

Status: review

## Story

As a user, I want meaningful icons throughout the UI, so that actions and information
are quicker to scan and the app looks finished (Epic 12, FR-UI2 / FR-UI6).

## Acceptance Criteria

1. `@mui/icons-material` icons are applied consistently across navigation, primary
   actions (upload, export, download, delete, add), status/severity indicators
   (vulnerability severity, version-currency badges, job status), and the report tabs.
2. Icon-only controls carry an accessible label (`aria-label`/tooltip).
3. A single icon vocabulary is used per concept (same icon everywhere), centralized so
   it isn't re-picked per component; icon color follows the 12.1 theme palette.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Added `frontend/src/icons.ts` — the central icon vocabulary: navigation icons, action
  icons, report-tab icons, and `severityIcon`/`currencyIcon`/`jobStatusIcon` helpers that
  return `{ Icon, color }` so a concept always renders the same icon + palette color.
- Navigation: `SideNav` items get leading icons (Upload/History/API Keys/Members).
- Header (`Layout`): the emoji account button → `AccountCircle` icon; Logout menu item
  gets a `Logout` icon. Existing icon-only controls already had `aria-label`s (theme
  toggle, repo/docs links, hamburger, account menu) — left intact.
- Report tabs (`ResultsPage`): each tab gets a start icon; tabs made scrollable so the
  icon+label row fits narrow widths.
- Status/severity: `JobStatusBadge` chip gets a status icon; `VulnerabilitiesTab`
  severity cell renders the shared severity icon (with `titleAccess`); `VersionsTab`
  currency badge gets the shared currency icon.
- Actions: export-to-Excel (`TableView`), download SBOM (`Download`), upload/choose-file
  (`CloudUpload`/`AttachFile`), create key (`Add`), revoke key (`DeleteOutlined`),
  expand/collapse-all (`UnfoldMore`/`UnfoldLess`), licenses accordion `ExpandMore`.
- Colors use the SvgIcon `color` prop (theme palette) — no hard-coded values. Scope kept
  to icon adoption; no layout/spacing restructure (12.4), theme change (12.1), favicon
  (12.7), or branding (12.5).
- Note: this `@mui/icons-material` build uses the `Outlined` suffix (e.g.
  `DeleteOutlined`, `HelpOutlineOutlined`) rather than `DeleteOutline`/`HelpOutline`.

### File List

- `frontend/src/icons.ts` (new)
- `frontend/src/icons.test.ts` (new)
- `frontend/src/components/SideNav.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/components/JobStatusBadge.tsx`
- `frontend/src/components/OverviewTab.tsx`
- `frontend/src/components/VulnerabilitiesTab.tsx`
- `frontend/src/components/VersionsTab.tsx`
- `frontend/src/components/LicensesTab.tsx`
- `frontend/src/pages/ResultsPage.tsx`
- `frontend/src/pages/UploadPage.tsx`
- `frontend/src/pages/KeysPage.tsx`
