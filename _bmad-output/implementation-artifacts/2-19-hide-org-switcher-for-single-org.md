# Story 2.19: Hide the Org Switcher When the User Has One or Fewer Orgs (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user who belongs to a single organization,
I want no pointless org-switcher dropdown,
so that the header only offers a switch control when there is actually something to switch to.

## Acceptance Criteria

1. **Dropdown only when there is a choice.** The org-switcher dropdown renders only when the user has **more than one** switchable org. `getOrgs()` already returns only non-ADMIN orgs (`get_user_orgs`, Story 2.12), so the test is simply `orgs.length > 1`. With exactly **one** org, no dropdown — show the org name statically, or omit the control entirely (the active org already appears in the account menu and the side-nav footer). With **zero** orgs, no dropdown.
2. **Create-org stays global-admin-only.** The "Create organization" / "New organization" affordance remains gated on `isGlobalAdmin` (Story 2.12) — a non-admin never sees it. This story does NOT loosen that gate: if a user sees the create affordance, they ARE a global admin. The zero-org branch keeps showing the create button only for a global admin (existing behavior).
3. **Tested.** `>1` org → dropdown renders (a `MenuItem` per org). Exactly `1` org → no dropdown; the org name is shown (or the control is absent). `0` orgs → no dropdown; the "Create organization" affordance appears only for a global admin (and not for a non-admin). `pixi run ci` is green.

## Tasks / Subtasks

- [ ] **Task 1 — Gate the dropdown on more than one org (AC: #1)**
  - [ ] `frontend/src/components/OrgSwitcher.tsx`: the component currently renders the `FormControl`/`Select` dropdown whenever `orgs.length > 0` (the only early return is the `orgs.length === 0` branch at line 44). Add a single-org branch: when `orgs.length === 1`, render the org name statically (e.g. a `Typography`) instead of the dropdown, or return the minimal control. Keep the `orgs.length === 0` branch (global-admin create button / null) as-is. Render the `Select` only when `orgs.length > 1`.
- [ ] **Task 2 — Confirm the create-org gate is unchanged (AC: #2)**
  - [ ] Verify the create affordance stays behind `isGlobalAdmin` in both the zero-org branch (`Create organization` button, lines 46-61) and the in-dropdown `New organization` `MenuItem` (guarded by `isGlobalAdmin`, lines 92-97). No change to the gate — just don't regress it while restructuring the branches.
- [ ] **Task 3 — Tests (AC: #3)**
  - [ ] `frontend/src/components/OrgSwitcher.test.tsx`: `getOrgs` returns 2 orgs → the `Select` (role `combobox`) renders with both org names. Returns 1 org → no `combobox`; the single org name is shown. Returns 0 orgs → no `combobox`; for `isGlobalAdmin=true` the "Create organization" button shows, for a non-global-admin nothing renders (returns null, existing behavior).

## Dev Notes

### Root cause

`frontend/src/components/OrgSwitcher.tsx` renders the dropdown whenever `orgs.length > 0` — the only guarded branch is `orgs.length === 0` (line 44), so a user with exactly **one** org still gets a `Select` with a single item and nothing to switch to. `getOrgs()` maps to `OrgListView` → `get_user_orgs`, which already excludes the ADMIN org, so `orgs` is the list of switchable (non-ADMIN) orgs; the fix is a length check of `> 1`.

### Notes

- The active org is not lost when the dropdown is hidden: it already appears in the account menu (Story 10.5) and the side-nav footer (`SideNav.tsx`), so a single-org user still sees which org they're in.
- Depends on / overlaps **Story 13.1** (global-admin management screen), which also touches `OrgSwitcher`/the auth context. Implement **after 13.1 merges**.
- Pairs with **Story 2.18**: a zero-org user is restricted to home, so the zero-org OrgSwitcher branch is only reachable by a global admin at the header on the home page — keep its create button.

### References

- `frontend/src/components/OrgSwitcher.tsx` (branch on `orgs.length`; the `Select`, the create button, the `New organization` `MenuItem`)
- `frontend/src/components/OrgSwitcher.test.tsx` (tests to extend)
- `frontend/src/components/Layout.tsx` (renders `OrgSwitcher`), `frontend/src/components/SideNav.tsx` (active-org footer)
- `backend/generate_sbom/users/selectors.py` (`get_user_orgs` — why `orgs` is already non-ADMIN)
- Related: `2-12-restrict-org-creation-to-global-admins.md`, `2-5-create-organization-from-the-ui.md`, `13-1-global-admin-management-screen.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
