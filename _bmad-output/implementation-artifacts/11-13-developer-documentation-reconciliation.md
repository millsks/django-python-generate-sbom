# Story 11.13: Developer Documentation Reconciliation (Global-Admin Model)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Implement AFTER Epic 2 is done. Verify the model/permission/setup details against the shipped code.

## Story

As a developer/contributor,
I want the developer docs to describe the org-membership and global-admin model as built,
so that I can reason about permissions and set up an environment correctly.

## Acceptance Criteria

1. **Architecture doc reflects the global-admin tier.** `docs/developer/architecture.md` documents the system ADMIN org (`Org.is_admin_org`) whose members are global admins provisioned as admins of all orgs, that this is a deliberate cross-org superuser tier, how permission checks treat global admins as org admins everywhere, and the zero-org/identity decoupling (auth is independent of org membership). (FR-DOC4)
2. **Data-model doc reflects the changes.** `docs/developer/data-model.md` `Org`/`OrgMembership`/`User` descriptions (and any diagram) reflect the `is_admin_org` flag, the zero-org state (users may have no memberships), and global-admin memberships.
3. **Setup doc reflects superuser bootstrap.** `docs/developer/setup.md` first-run/superuser steps are accurate: the initial superuser is seeded into the ADMIN org (via `bootstrap_admin_org` / the superuser hook), not an auto-created personal org. `pixi run docs-build` (strict) passes.

## Tasks / Subtasks

- [ ] **Task 1 — Architecture (AC: #1)**
  - [ ] Update `docs/developer/architecture.md`: add the global-admin tier and permission model; note global admins hold real `OrgMembership(role=ADMIN)` rows in every org (so authorization needs no special-casing); describe zero-org identity decoupling (`auth/me`).
- [ ] **Task 2 — Data model (AC: #2)**
  - [ ] Update `docs/developer/data-model.md`: `Org.is_admin_org`, zero-membership users, global-admin memberships; refresh any ER/relationship diagram.
- [ ] **Task 3 — Setup (AC: #3)**
  - [ ] Update `docs/developer/setup.md`: superuser bootstrap via the `bootstrap_admin_org` management command / `create_superuser` hook; remove any "personal org on first user" assumption.
- [ ] **Task 4 — Build + code reference (AC: #3)**
  - [ ] Confirm the mkdocstrings code reference (`docs/developer/code-reference.md`) still renders the new/updated services (e.g. `grant_global_admin`); `pixi run docs-build` (strict) green.

## Dev Notes

### Epic 2 model facts to document

- `Org.is_admin_org: bool` (one distinguished ADMIN org). Members of the ADMIN org = **global admins**. `create_org` auto-provisions global admins; `grant_global_admin` back-fills existing orgs (Story 2.8).
- Users may have **zero** memberships (Story 2.6). Identity via `GET /auth/me/`, decoupled from active org.
- Superuser seeding: data migration creates the ADMIN org; `create_superuser` / `bootstrap_admin_org` makes superusers global admins. Confirm the exact mechanism shipped (see the 2.8 story / final code).

### Scope / coordination

- Developer/architecture audience only. End-user narrative → **11.11**; API contract → **11.12**; README + general sweep → **11.14**.

### Project Structure Notes

- Docs under `docs/developer/`. Code reference is auto-generated via `mkdocstrings` from backend docstrings. Build gate: `pixi run docs-build`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 11.13]
- Epic 2 story: `_bmad-output/implementation-artifacts/2-8-global-admin-org-and-cross-org-provisioning.md`
- Docs: `docs/developer/architecture.md`, `docs/developer/data-model.md`, `docs/developer/setup.md`, `docs/developer/code-reference.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
