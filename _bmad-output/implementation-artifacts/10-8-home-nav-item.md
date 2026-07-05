# Story 10.8: Add a Home Side-Nav Item

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an authenticated user,
I want a "Home" item at the top of the side navigation,
so that I can return to the index/landing page (Story 12.8) without relying on the brand mark.

## Acceptance Criteria

1. **Home item, first, for everyone.** The side navigation shows a **Home** entry (→ `/`) as the first item for all authenticated users. Final order: **Home, Upload, History, Members, API Keys, Organization** — Members and Organization stay admin-gated (non-admins see Home, Upload, History, API Keys).
2. **Active only on `/`.** Because `/` is a prefix of every route, the Home `NavLink` uses react-router's `end` prop so it is highlighted **only** on the index page — other items still highlight on their own routes.
3. **Tested.** Order + presence for admin and non-admin, and the active-only-on-`/` behavior.

## Tasks / Subtasks

- [ ] **Task 1 — Icon + nav item (AC: #1)**
  - [ ] `frontend/src/icons.ts`: add `home: HomeIcon` (`@mui/icons-material/Home`) to `NavIcon`.
  - [ ] `frontend/src/components/SideNav.tsx`: add `{ to: '/', label: 'Home', Icon: NavIcon.home, end: true }` as the first `items` entry; add an optional `end?: boolean` to `NavDest` and pass `end={item.end}` to the `NavLink`.
- [ ] **Task 2 — Tests (AC: #3)**
  - [ ] `SideNav.test.tsx`: assert the admin order `[Home, Upload, History, Members, API Keys, Organization]`, the non-admin order `[Home, Upload, History, API Keys]`, and that Home has `aria-current="page"` on `/` but not on `/upload`.

## Dev Notes

- The top-left brand mark already links to `/`; this adds an explicit, discoverable Home destination in the side rail.
- `Layout.test.tsx` uses targeted `getByRole` lookups (no exact-count assertion), so the extra item is compatible.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 10.8: Add a Home Side-Nav Item]
- `frontend/src/components/SideNav.tsx`, `frontend/src/icons.ts`; related: Story 2.15 (nav order), 12.8 (landing page), 10.7 (login → `/`)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
