# Story 11.17: Developer/Architecture Documentation Reconciliation (Admin Tier, 2nd Pass)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Implement against the **then-current merged state** — at minimum through **Story 13.1**. **Recommended:** run after Stories 2.18–2.20 merge so the org-access refinements are captured. Verify the model/permission/setup details against the shipped code.

## Story

As a developer/contributor,
I want the developer docs to describe the org/admin/auth model, authorization, and the version-currency changes as built,
so that I can reason about permissions and the codebase correctly.

## Acceptance Criteria

1. **Architecture doc reflects the org/admin/auth model.** `docs/developer/architecture.md` documents the org-membership model, **per-org admin vs. global admin**, the system **ADMIN org** (`Org.is_admin_org`) + cross-org provisioning, the **admin-route + API authorization** pattern (AdminRoute / admin-only pages, gated at BOTH route and API — Story 2.17), **promote/demote** (per-org, Stories 2.16/2.20), and zero-org/identity decoupling (`auth/me` independent of org membership). (FR-DOC4)
2. **Data-model doc reflects the changes.** `docs/developer/data-model.md` `Org`/`OrgMembership`/`User` descriptions (and any diagram) reflect the `is_admin_org` flag, the zero-org state (users may have no memberships), global-admin memberships, and the member/admin `role`.
3. **Setup doc reflects superuser seeding.** `docs/developer/setup.md` first-run steps document env-driven superuser seeding (`seed_superuser` / the superuser hook) that provisions the initial superuser into the ADMIN org — not an auto-created personal org (Story 2.13).
4. **Version-currency / conda-forge changes documented; code reference renders; strict build green.** `docs/developer/architecture.md` (and/or `code-reference.md`) covers the version-currency **PyPI Latest** column + Excel red divergence (Stories 8.22/8.23) and the conda-forge `python-<name>` disambiguation (8.24). The mkdocstrings code reference (`docs/developer/code-reference.md`) still renders the new/updated services (e.g. `grant_global_admin`, `revoke_global_admin`, `promote_member_to_admin`). `pixi run docs-build` (strict) passes.

## Tasks / Subtasks

- [ ] **Task 1 — Architecture (AC: #1)**
  - [ ] Update `docs/developer/architecture.md`: org-membership model; per-org admin vs. global admin (ADMIN org + provisioning); the admin-route + API-authorization pattern (Story 2.17); promote/demote (2.16/2.20); zero-org identity decoupling (`auth/me`).
- [ ] **Task 2 — Data model (AC: #2)**
  - [ ] Update `docs/developer/data-model.md`: `Org.is_admin_org`, zero-membership users, global-admin memberships, `OrgMembership.role`; refresh any ER/relationship diagram.
- [ ] **Task 3 — Setup (AC: #3)**
  - [ ] Update `docs/developer/setup.md`: env-driven `seed_superuser` bootstrap into the ADMIN org (Story 2.13); remove any "personal org on first user" assumption.
- [ ] **Task 4 — Version-currency + build + code reference (AC: #4)**
  - [ ] Document the PyPI-Latest column + Excel red divergence (8.22/8.23) and conda-forge `python-<name>` disambiguation (8.24). Confirm mkdocstrings renders the new/updated services; `pixi run docs-build` (strict) green.

## Dev Notes

### Model / authorization facts to document (verify against code)

- `Org.is_admin_org: bool` — the one distinguished ADMIN org. Members = **global admins**, provisioned as admin of every org. Services: `grant_global_admin` / `grant_global_admin_by_email` / `revoke_global_admin` / `is_global_admin` / `get_admin_org` in `backend/generate_sbom/users/services.py`.
- Per-org admin is separate: `promote_member_to_admin` (2.16) and demote (2.20). Do not conflate per-org admin with the global tier.
- **Authorization** (Story 2.17): admin-only pages enforced at BOTH the frontend route (`AdminRoute`) and the API (403). `auth/me` exposes `is_admin` / `is_global_admin` for gating.
- Zero-org users (Story 2.6) — identity via `GET /auth/me/`, decoupled from active org; zero-org users restricted to home (2.18).
- Superuser seeding: env-driven `seed_superuser` provisions the superuser into the ADMIN org (Story 2.13).
- Version currency: PyPI-Latest column + conda-forge-latest divergence red text carried into Excel (8.22/8.23); conda-forge `python-<name>` reverse-lookup disambiguation (8.24).

### Scope / coordination

- Developer/architecture audience only. End-user narrative → **11.15**; API contract → **11.16**; README + general sweep → **11.18**.
- Second pass: **11.13** covered the initial ADMIN-org / zero-org / superuser-bootstrap model; this pass adds authorization (2.17), promote/demote, and the version-currency/conda-forge changes.

### Project Structure Notes

- Docs under `docs/developer/`. Code reference is auto-generated via `mkdocstrings` from backend docstrings. Build gate: `pixi run docs-build`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 11.17]
- Code: `backend/generate_sbom/users/services.py`, `views.py`
- Epic 2 stories: `2-8`, `2-13`, `2-16`, `2-17`, `2-20`; Epic 8: `8-22`, `8-23`, `8-24`
- Prior pass: `11-13-developer-documentation-reconciliation.md`
- Docs: `docs/developer/architecture.md`, `data-model.md`, `setup.md`, `code-reference.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
</content>
