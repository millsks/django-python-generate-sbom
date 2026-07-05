# Story 12.4: Page-Level Visual Polish & States

Status: review

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Added shared loading/empty/error state components (`components/PageState.tsx`:
  `LoadingState`, `EmptyState`, `ErrorState`) so every data-fetching page handles its
  async states the same way, on the 12.1 theme. Complements the existing
  `TabFailureNotice`.
- **KeysPage / MembersPage** (previously bare tables with no loading or empty state):
  now show a `LoadingState` on first load, an `EmptyState` (with a nav-vocabulary icon)
  when there are none, and render the list inside an outlined `Paper` `TableContainer`
  (horizontal scroll on small screens). The create/add form moved into an outlined
  `Paper` "section card" with a heading and a responsive column→row layout.
- **HistoryPage:** its ad-hoc `Alert`/`CircularProgress` states are replaced by the
  shared `ErrorState` / `LoadingState` / `EmptyState` (same "No jobs yet." text and
  "Loading jobs" label the tests assert), and the jobs table sits in an outlined
  `Paper` `TableContainer`.
- **UploadPage / LoginPage / RegisterPage:** the forms are wrapped in a consistent
  outlined `Paper` card (padding + column layout) for a cohesive "form card" look.
- **DashboardPage:** the placeholder body sits in an outlined `Paper` card with muted
  text.
- Consistency + responsiveness: spacing/typography/color come from theme tokens (no
  hard-coded values); tables scroll within their `TableContainer`; forms collapse to a
  single column on `xs`. Used `Box` + `sx` (not `Stack`) for responsive form layouts to
  avoid this MUI version's `Stack` `component`/responsive-prop typing overloads.
- Icon usage stays within the `icons.ts` vocabulary (Story 12.2); `theme.ts` (12.1) and
  the `Layout` shell (12.3) were not modified.

### File List

- `frontend/src/components/PageState.tsx` (new)
- `frontend/src/components/PageState.test.tsx` (new)
- `frontend/src/pages/KeysPage.tsx` (loading/empty states, table + form cards)
- `frontend/src/pages/MembersPage.tsx` (loading/empty states, table + form cards)
- `frontend/src/pages/HistoryPage.tsx` (shared states + table card)
- `frontend/src/pages/UploadPage.tsx` (form card)
- `frontend/src/pages/LoginPage.tsx` (form card)
- `frontend/src/pages/RegisterPage.tsx` (form card)
- `frontend/src/pages/DashboardPage.tsx` (placeholder card)
