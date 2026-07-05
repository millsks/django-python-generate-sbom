# Story 2.14: Create-Organization Dialog Label Clipped (Bugfix)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user creating an organization,
I want the "Organization name" field label to be fully visible,
so that the dialog looks correct and the field is clearly labeled.

## Acceptance Criteria

1. **Label not clipped.** In the Create Organization dialog, the full "Organization name" label renders above the outlined `TextField` (not cut off).
2. **Dialog still looks correct.** Title spacing, the error state, and the Cancel/Create actions are unaffected.
3. **CI green.** The existing `CreateOrgDialog` render test still passes; `pixi run ci` is green.

## Tasks / Subtasks

- [x] **Task 1 — Give the floating label clearance (AC: #1, #2)**
  - [x] `frontend/src/components/CreateOrgDialog.tsx`: `DialogContent`'s `pt: 1` (8px) is too small — the scroll area clips the outlined field's floating label (which sits above the input's top border). Increase the top padding (`pt: 2`) and add a small top margin to the `TextField` (`sx={{ mt: 1 }}`).
- [x] **Task 2 — Verify (AC: #3)**
  - [x] Existing `CreateOrgDialog.test.tsx` render test still passes; `pixi run ci` green.

## Dev Notes

- Root cause: `<DialogContent sx={{ ..., pt: 1 }}>` in `CreateOrgDialog.tsx`. MUI outlined labels float ~9px above the input's top border; 8px top padding clips them within `DialogContent`'s scroll area.
- Pure CSS/layout fix — pixel clipping isn't unit-testable, so no new assertion is fabricated; the existing render test guards structure.

### References

- `frontend/src/components/CreateOrgDialog.tsx` (DialogContent `pt`, the `TextField`)
- Related: `2-5-create-organization-from-the-ui.md`, `2-6-zero-org-users-and-identity-decoupling.md` (dialog origin)

## Dev Agent Record

### Agent Model Used

Opus 4.8 (1M context)

### Debug Log References

### Completion Notes List

- Fixed by increasing `DialogContent` top padding to `pt: 2` and adding `sx={{ mt: 1 }}` to the `TextField`.

### File List

- `frontend/src/components/CreateOrgDialog.tsx`
