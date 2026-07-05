# Story 2.15: Reorder the Left Side Navigation (Bugfix)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want the side-navigation destinations in a sensible order,
so that related items sit together and the admin links aren't appended out of place.

## Acceptance Criteria

1. **Admin order.** For an admin, the side nav is ordered **Upload, History, Members, API Keys, Organization** — Members between History and API Keys, Organization last (both admin-only).
2. **Non-admin unchanged.** A non-admin sees Upload, History, API Keys with no Members/Organization links.
3. **Tested; CI green.** `SideNav.test.tsx` asserts the admin order; `pixi run ci` is green.

## Tasks / Subtasks

- [x] **Task 1 — Interleave the ordered list (AC: #1, #2)**
  - [x] `frontend/src/components/SideNav.tsx`: replace the `NAV_ITEMS` + `adminItems` split (which appended admin links) with a single ordered `items` list that spreads the admin-only Members and Organization links into their correct positions via `...(isAdmin ? [...] : [])`.
- [x] **Task 2 — Tests (AC: #3)**
  - [x] `SideNav.test.tsx`: assert `getAllByRole('link')` order is `['Upload','History','Members','API Keys','Organization']` for an admin; existing presence/absence tests still hold. `Layout.test.tsx` needs no change (it asserts presence, not order).

## Dev Notes

- Prior order (bug): `[...NAV_ITEMS, ...adminItems]` = Upload, History, API Keys, Organization, Members.
- Non-admin path is unchanged (the admin-only spreads collapse to nothing).

### References

- `frontend/src/components/SideNav.tsx`, `frontend/src/components/SideNav.test.tsx`
- Related: `2-11-org-maintenance-navigation-for-admins.md` (Organization entry), Story 12.3 (side nav)

## Dev Agent Record

### Agent Model Used

Opus 4.8 (1M context)

### Debug Log References

### Completion Notes List

- Single interleaved `items` list; added an order assertion to `SideNav.test.tsx`.

### File List

- `frontend/src/components/SideNav.tsx`
- `frontend/src/components/SideNav.test.tsx`
