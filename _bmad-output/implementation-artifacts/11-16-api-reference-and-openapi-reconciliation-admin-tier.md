# Story 11.16: API Reference & OpenAPI Reconciliation (Admin Tier, 2nd Pass)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Implement against the **then-current merged state** — at minimum through **Story 13.1**. **Recommended:** run after Stories 2.18–2.20 merge so any access-scope refinements are captured. Verify request/response shapes against the live API (and the rendered Swagger UI) before finalizing.

## Story

As an API consumer,
I want the REST API reference and the generated OpenAPI/Swagger to match all the current endpoints,
so that I can integrate against accurate request/response contracts for the admin and global-admin surfaces.

## Acceptance Criteria

1. **Authentication reference reflects `is_admin`/`is_global_admin`.** `docs/api/authentication.md` documents `GET /api/v1/auth/me/` returning the current user with **`is_admin`** (admin of the active org) and **`is_global_admin`** flags (Stories 2.6, 2.12), alongside register/login/logout. (FR-DOC5)
2. **Organizations reference covers the full membership surface.** `docs/api/organizations.md` documents: add-existing-by-email member endpoint (`POST /orgs/members/`), **create-new-user** (`POST /orgs/members/create-user/`, Story 2.10), **promote-admin** (`POST /orgs/promote-admin/`, Story 2.16), member remove (`DELETE /orgs/members/<user_id>/`), and create-org (`POST /orgs/create/`, global-admin-gated — Story 2.12), each with request/response shapes and error codes (`no_such_user`, etc.).
3. **Global-admin section added.** `docs/api/organizations.md` (or a dedicated admin/global-admin section) documents the global-admin endpoints: `GET /admin/global-admins/` (list), `POST /admin/global-admins/` (grant by email), `DELETE /admin/global-admins/<user_id>/` (revoke = remove-from-ADMIN + demote-everywhere), all global-admin-gated (403 otherwise), including the `last_global_admin` guard error (Story 13.1).
4. **OpenAPI/Swagger in sync.** The generated OpenAPI schema + Swagger UI (Story 11.9) reflect the new/changed endpoints; regenerate any committed schema artifact if one exists, and confirm the docs match what Swagger renders. (FR-DOC9) `pixi run docs-build` (strict) passes.

## Tasks / Subtasks

- [ ] **Task 1 — Authentication endpoints (AC: #1)**
  - [ ] Update `docs/api/authentication.md`: `GET /auth/me/` returns `{id, email, is_admin, is_global_admin}` (auth required; 403 anon).
- [ ] **Task 2 — Organizations & membership endpoints (AC: #2)**
  - [ ] Update `docs/api/organizations.md`: `POST /orgs/members/` (add-existing by email; `no_such_user`), `POST /orgs/members/create-user/` (create-new-user), `POST /orgs/promote-admin/` (promote), `DELETE /orgs/members/<user_id>/` (remove), `POST /orgs/create/` (global-admin-gated).
- [ ] **Task 3 — Global-admin section (AC: #3)**
  - [ ] Add a global-admin API section: `GET`/`POST`(grant-by-email)/`DELETE` on `admin/global-admins/`, the 403 envelope for non-global-admins, and the `last_global_admin` guard error.
- [ ] **Task 4 — OpenAPI/Swagger + build (AC: #4)**
  - [ ] Confirm how the schema is served (Story 11.9); if a schema file is committed, regenerate it. Verify Swagger renders the new endpoints; reconcile markdown to match. `pixi run docs-build` (strict) green.

## Dev Notes

### Endpoints to document (verified in code)

From `backend/generate_sbom/users/urls.py` and `views.py`:

- `GET /api/v1/auth/me/` → `{id, email, is_admin, is_global_admin}` (`AuthMeView`; `is_admin` = admin of active org, `is_global_admin` = ADMIN-org member). Auth required; 403 anon.
- `POST /api/v1/orgs/create/` → global-admin-gated (`CreateOrgView`; 403 for non-global-admins).
- `POST /api/v1/orgs/members/` → add existing user by email (`MembersView`).
- `POST /api/v1/orgs/members/create-user/` → create a new user account for the org (`CreateMemberUserView`, Story 2.10).
- `POST /api/v1/orgs/promote-admin/` → promote a member to admin (`PromoteAdminView`, admin-only, Story 2.16).
- `DELETE /api/v1/orgs/members/<user_id>/` → remove member (`MemberDetailView`).
- `GET /api/v1/admin/global-admins/` → list global admins (`GlobalAdminsView`, global-admin-gated).
- `POST /api/v1/admin/global-admins/` → grant global admin by email (`grant_global_admin_by_email`; unknown email → error).
- `DELETE /api/v1/admin/global-admins/<user_id>/` → revoke (`GlobalAdminDetailView`; removes from ADMIN org + demotes to member in every non-admin org; `last_global_admin` guard blocks removing the last one).

Verify these against the running backend and the Swagger UI rather than trusting this note verbatim (codes/messages may be refined).

### Scope / coordination

- API-contract docs only. User-journey narrative is **11.15**; architecture/permission model is **11.17**. The OpenAPI generator is the source of truth — reconcile prose to it, not the reverse.
- Second pass: **11.12** covered `auth/me` + email-add + create-org initially; this pass adds `is_admin`/`is_global_admin`, create-user, promote-admin, and the global-admin management endpoints.

### Project Structure Notes

- Docs under `docs/api/`. Schema/Swagger served by the backend (Story 11.9 — inspect `backend/` URL config). Build gate: `pixi run docs-build`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 11.16]
- Code: `backend/generate_sbom/users/urls.py`, `backend/generate_sbom/users/views.py`
- Prior pass: `11-12-api-reference-and-openapi-reconciliation.md`
- Docs: `docs/api/authentication.md`, `docs/api/organizations.md`

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Opus 4.8, 1M context)

### Debug Log References

- `pixi run docs-build` (`mkdocs build --strict`) — green.
- `pixi run ci` — green.

### Completion Notes List

- Reconciled prose against `users/urls.py`, `users/views.py`, and `users/serializers.py` (the drf-spectacular schema is generated at runtime — there is no committed schema artifact to regenerate).
- `authentication.md`: `GET /auth/me/` now documents the `{id, email, is_admin, is_global_admin}` response with a field table (`is_admin` = admin of the active org, `is_global_admin` = ADMIN-org member). Kept the accurate `401`-anon behavior (the Api-Key authenticator sets `WWW-Authenticate`, so DRF renders anon as 401, per `test_auth_me_requires_authentication`).
- `organizations.md`: create-org marked **global-admin gated** (403 `not_global_admin`); added `POST /orgs/members/create-user/` (`email_taken`), `POST /orgs/promote-admin/` and `POST /orgs/demote-admin/` (204; `user_id` body); replaced the stale `transfer-admin` endpoint; added a **Global-admin management** section — `GET`/`POST`(grant-by-email, `no_such_user`)/`DELETE`(revoke, `last_global_admin`) on `admin/global-admins/`.
- `api/index.md`: refreshed the Organizations group description and the error-code list (`not_global_admin`, `last_global_admin`, `no_such_user`, `already_member`, `email_taken`, `last_admin`, `global_admin_protected`).

### File List

- `docs/api/authentication.md`
- `docs/api/organizations.md`
- `docs/api/index.md`
</content>
