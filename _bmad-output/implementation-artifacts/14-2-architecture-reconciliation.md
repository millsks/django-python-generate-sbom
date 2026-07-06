# Story 14.2: Architecture Reconciliation (Org/Admin/Auth Model & Diagrams)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Reconcile the architecture to the **then-current merged state** — at minimum through **Story 13.1**. **Recommended:** run after Stories 2.18–2.20 merge so the org-access refinements are captured. Verify against the shipped code.

## Story

As an architect,
I want the architecture artifacts and diagrams to document the org/admin/auth model and the global-admin tier,
so that the architecture spine reflects the system as built and downstream work stays consistent.

## Acceptance Criteria

1. **Spine documents the org/admin/auth model.** `ARCHITECTURE-SPINE.md` gains coverage (an invariant/AD entry and/or the entity-relationship + capability-map sections) for: the org-membership model, per-org admin vs. **global admin** (the ADMIN org, `Org.is_admin_org`, + cross-org provisioning), **admin authorization** enforced at both the route and the API, zero-org/identity decoupling (`auth/me`), and promote/demote. (Consistent with AD-2 OrgScopedModel.)
2. **Solution design + one-pager updated.** `solution-design.md` and `one-pager.md` describe the account/org/admin model and the global-admin tier (not the old personal-org model), including the new endpoints/flows (`auth/me`, create-org gating, add-by-email/create-user, promote/demote, global-admin management).
3. **Diagrams refreshed.** `architecture-diagrams.html` is updated so the entity/relationship view includes the **ADMIN org / `is_admin_org` / roles / global-admin memberships** and the zero-org state, and the flow diagrams reflect the new endpoints (auth/me, admin/global-admins, promote-admin, members/create-user). Diagrams no longer predate the org/admin model.

## Tasks / Subtasks

- [x] **Task 1 — Architecture spine (AC: #1)**
  - [x] Update `ARCHITECTURE-SPINE.md`: add the org/admin/auth model — global-admin tier (ADMIN org + provisioning), admin authorization (route + API), zero-org identity decoupling, promote/demote — in the Invariants/AD and/or Core-entity-relationships + Capability→Architecture-Map sections.
- [x] **Task 2 — Solution design + one-pager (AC: #2)**
  - [x] Update `solution-design.md` and `one-pager.md` to describe the account/org/admin model and the global-admin tier and the new endpoints/flows; remove any personal-org-on-registration assumption.
- [x] **Task 3 — Diagrams (AC: #3)**
  - [x] Update `architecture-diagrams.html`: entities (ADMIN org / `is_admin_org` / roles / global-admin memberships / zero-org state) and flows (auth/me, create-org gating, add-by-email/create-user, promote-admin, admin/global-admins list/grant/revoke).

## Dev Notes

### The model to encode (verify against code)

- **Global-admin tier:** `Org.is_admin_org` marks the one ADMIN org; its members are global admins provisioned as admin of every org. Services `grant_global_admin` / `grant_global_admin_by_email` / `revoke_global_admin` / `is_global_admin` / `get_admin_org` in `backend/generate_sbom/users/services.py`.
- **Authorization** (Story 2.17): admin-only pages enforced at BOTH the frontend route (`AdminRoute`) and the API (403). `auth/me` carries `is_admin` / `is_global_admin`.
- **Zero-org / identity decoupling** (2.6): identity via `GET /auth/me/`, decoupled from active org; zero-org users restricted to home (2.18).
- **Endpoints/flows** (`backend/generate_sbom/users/urls.py`): `auth/me/`, `orgs/create/` (global-admin-gated), `orgs/members/`, `orgs/members/create-user/`, `orgs/promote-admin/`, `orgs/members/<id>/`, `admin/global-admins/` (list/grant), `admin/global-admins/<id>/` (revoke).
- **Consistency with AD-2:** the model still respects OrgScopedModel org isolation; global admins hold real `OrgMembership(role=ADMIN)` rows in every org, so authorization needs no special-casing.

### Scope / coordination

- Architecture planning artifacts only — this story does NOT edit `docs/**` or code (that is Epic 11's reopened stories). PRD is **14.1**.

### Project Structure Notes

- Files under `_bmad-output/planning-artifacts/architecture/architecture-django-python-generate-sbom-2026-07-03/`: `ARCHITECTURE-SPINE.md`, `solution-design.md`, `one-pager.md`, `architecture-diagrams.html`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 14.2]
- Epic 2 stories: `2-6`, `2-8`, `2-12`, `2-16`, `2-17`, `2-20`; Story `13-1-global-admin-management-screen.md`
- Code: `backend/generate_sbom/users/{urls,views,services}.py`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (1M context)

### Debug Log References

- Verified the model against code before editing: `backend/generate_sbom/users/{urls,views,services,models,auth}.py` — `Org.is_admin_org`, `is_global_admin`/`get_the_admin_org`/`grant_global_admin`/`grant_global_admin_by_email`/`revoke_global_admin`, `create_org` provisioning, promote/demote guards, `auth/me` (`is_admin`/`is_global_admin`), `get_request_org`/`get_admin_org` (session active-org excludes the ADMIN org), env-seeded superuser → global admin.
- `pixi run ci` — planning-artifact-only change; no code/`docs/**` touched.

### Completion Notes List

- **AC #1 (spine).** Added invariant **AD-14 — Org/admin/auth model** (zero-org identity; per-org vs. global admin with cross-org provisioning; global-admin-gated org creation + management; promote/demote; authorization at both SPA route and API). Updated the Core-entity-relationships ERD (`Org.is_admin_org`, `OrgMembership.role`, zero-org note) and the Capability→Architecture-Map F1 row to reference AD-14. Consistent with AD-2 (global admins hold real `role=admin` memberships, so no special-casing).
- **AC #2 (solution design + one-pager).** `solution-design.md`: `Org.is_admin_org` in the model, an AD-14 org/admin/auth prose block, a corrected two-path auth convention (`request.auth.org` vs. session `get_request_org`/`get_admin_org`), the full `users/services.py` + domain-error surface, an expanded endpoint inventory (zero-org register, `auth/me`, orgs create/switch/leave, add-existing/create-user, promote/demote, global-admins list/grant/revoke, with an Auth column distinguishing Api-Key vs. Session), and a new "Admin authorization and the global-admin tier" security subsection. `one-pager.md`: added a business-level "Teams and Access" section (sign-up-then-added zero-org onboarding, per-org admin vs. global administrator, guarded invariants).
- **AC #3 (diagrams).** `architecture-diagrams.html`: added `is_admin_org` to the `Org` ERD entity + a zero-org/global-admin note; added a new **Org & Admin Flows** sequence diagram (register→zero-org, auth/me, global-admin-gated create-org, add-by-email/create-user, promote/demote, global-admins list/grant/revoke) with a nav link; added an AD-14 decision card and bumped the decision count. Kept the file self-contained and valid.
- Kept each artifact's existing structure and voice; no code or `docs/**` edits (Epic 11 owns docs; PRD is Story 14.1).

### File List

- `_bmad-output/planning-artifacts/architecture/architecture-django-python-generate-sbom-2026-07-03/ARCHITECTURE-SPINE.md`
- `_bmad-output/planning-artifacts/architecture/architecture-django-python-generate-sbom-2026-07-03/solution-design.md`
- `_bmad-output/planning-artifacts/architecture/architecture-django-python-generate-sbom-2026-07-03/one-pager.md`
- `_bmad-output/planning-artifacts/architecture/architecture-django-python-generate-sbom-2026-07-03/architecture-diagrams.html`
</content>
