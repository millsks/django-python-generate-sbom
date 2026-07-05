# Story 2.5: Create Organization from the UI

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to create a new organization from the app,
so that I can start a workspace without hitting the API directly.

## Acceptance Criteria

1. **Create-org UI.** The backend `POST /api/v1/orgs/create/` (`CreateOrgView`) and the frontend `createOrg()` already exist but are not exposed in the UI. Add a "Create organization" control (a "+ New organization" item in the org switcher menu and/or a button on the Members page) that opens a small dialog (org name), calls `createOrg()`, and on success switches into the new org.
2. **Creator is admin; global admins auto-added.** A newly created org has the creating user as its admin, and **all global admins are auto-added as admins** (Story 2.8 provisioning) so oversight is preserved.
3. **Appears in switcher; scoped to it.** The new org appears in the org switcher and the user is scoped to it. Covered by a test.

## Tasks / Subtasks

- [ ] **Task 1 — Create-org dialog + trigger (AC: #1, #3)**
  - [ ] Add a create-org dialog component (MUI `Dialog` + a name `TextField`), calling `createOrg(name)` (`frontend/src/api/orgs.ts:33`) on submit.
  - [ ] Add the trigger: a "+ New organization" item in `OrgSwitcher` (`frontend/src/components/OrgSwitcher.tsx`) and/or a button on `MembersPage`. **Coordinate with Story 2.6:** 2.6 already replaces the `OrgSwitcher` zero-org `return null` with a create-org affordance — reuse the same dialog so there is one create-org path, not two.
  - [ ] On success, switch into the new org: either call `switchOrg(newOrg.slug)` then `window.location.reload()` (the switcher's existing pattern), or refresh `AuthProvider` state so `activeOrg` becomes the new org.
- [ ] **Task 2 — Verify backend provisioning (AC: #2)**
  - [ ] `create_org()` (`backend/generate_sbom/users/services.py:30`) already makes the creator an admin. Auto-adding global admins is delivered by **Story 2.8** (`_provision_global_admins`). If 2.8 is not yet merged, this AC is a no-op (no global admins exist); do **not** re-implement provisioning here. If 2.8 is merged, confirm `create_org` calls it.
- [ ] **Task 3 — Tests (AC: #3)**
  - [ ] Frontend (Vitest + RTL, mock `../api/orgs`): creating an org calls `createOrg`, then the new org is active / appears in the switcher.
  - [ ] Backend `create_org` admin-membership behavior is already covered by `test_orgs.py`; add coverage only if the create flow changes.

## Dev Notes

### This story is mostly frontend wiring — the backend already exists

- `CreateOrgView` (`backend/generate_sbom/users/views.py:194-203`) → `POST /orgs/create/`, returns `{slug, name}` 201. `create_org()` service (`services.py:30-37`) creates the org + admin membership. `createOrg(name)` client (`frontend/src/api/orgs.ts:33`) is defined **but currently called by no component** (per exploration) — this story is its first consumer.
- `OrgSwitcher` (`frontend/src/components/OrgSwitcher.tsx`): fetches `getOrgs()` on mount; `handleChange` → `switchOrg(slug)` + `window.location.reload()`; renders `null` when zero orgs (Story 2.6 changes that). The create control lives here and/or on `MembersPage`.

### Cross-story coordination

- **Story 2.6** introduces the no-org empty state with a create-org affordance and decouples auth from active org. 2.5 and 2.6 both need the create-org dialog — build it once and share it. Recommended order: land 2.6's auth/empty-state work first (or together), then 2.5's explicit switcher/Members entry point.
- **Story 2.8** provides global-admin auto-provisioning referenced by AC #2. 2.5 must not duplicate it.

### Testing standards

- Frontend: Vitest + React Testing Library, `*.test.tsx` co-located, **no MSW** — mock `../api/orgs` with `vi.mock`. Backend: pytest `@pytest.mark.django_db`, DRF `APIClient`, `backend/tests/unit/`.

### Project Structure Notes

- No backend model or endpoint changes expected. Frontend under `frontend/src/{components,pages,api}`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.5: Create Organization from the UI] (lines 533-555)
- Backend: `backend/generate_sbom/users/views.py:194`, `services.py:30`
- Frontend: `frontend/src/api/orgs.ts:33`, `components/OrgSwitcher.tsx`, `pages/MembersPage.tsx`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
