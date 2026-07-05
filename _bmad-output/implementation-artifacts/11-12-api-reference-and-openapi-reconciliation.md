# Story 11.12: API Reference & OpenAPI/Swagger Reconciliation

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Prerequisite:** Implement AFTER Epic 2 is done. Verify request/response shapes against the live API (and the rendered Swagger UI) before finalizing.

## Story

As an API consumer,
I want the REST API reference and the generated OpenAPI/Swagger to match the live endpoints,
so that I can integrate against accurate request/response contracts.

## Acceptance Criteria

1. **Authentication reference.** `docs/api/authentication.md` documents the new `GET /api/v1/auth/me/` identity endpoint (auth required, returns the current user `{id, email}`) and the updated `POST /auth/register/` response (`org: null`, zero-org registration), alongside login/logout. (FR-DOC5)
2. **Organizations & membership reference.** `docs/api/organizations.md` is accurate for: the members endpoint (email-only add payload, `temp_password` dropped, the "no such user" error), the create-org endpoint, and global-admin provisioning behavior.
3. **OpenAPI/Swagger in sync.** The generated OpenAPI schema + Swagger UI (Story 11.9) reflect the new/changed endpoints; regenerate any committed schema artifact if one exists, and confirm the docs match what Swagger renders. (FR-DOC9) `pixi run docs-build` (strict) passes.

## Tasks / Subtasks

- [ ] **Task 1 — Authentication endpoints (AC: #1)**
  - [ ] Update `docs/api/authentication.md`: add `GET /auth/me/` (200 `{id, email}` when authenticated, 403 otherwise); update the register response to `{"user": {...}, "org": null}`.
- [ ] **Task 2 — Organizations & membership endpoints (AC: #2)**
  - [ ] Update `docs/api/organizations.md`: `POST /orgs/members/` now takes `{ "email": ... }` (no `temp_password`) and returns `no_such_user` on an unknown email; document `POST /orgs/create/` and the global-admin auto-provisioning note.
- [ ] **Task 3 — OpenAPI/Swagger (AC: #3)**
  - [ ] Confirm how the schema is served (Story 11.9 endpoint) and whether a schema file is committed. If committed, regenerate it. Verify Swagger UI renders `auth/me` and the changed member/register shapes; reconcile the markdown to match.
- [ ] **Task 4 — Build (AC: #3)**
  - [ ] `pixi run docs-build` (strict) green.

## Dev Notes

### Exact contracts (from the Epic 2 implementation)

- `GET /api/v1/auth/me/` → **200** `{"id": <int>, "email": <str>}` (auth required; **403** anon). New in Story 2.6.
- `POST /api/v1/auth/register/` → **201** `{"user": {"id","email"}, "org": null}` (Story 2.6 — no personal org).
- `POST /api/v1/orgs/members/` → body `{"email": ...}`; unknown email → 400 `{"error": ..., "code": "no_such_user"}` (Story 2.7 — no more `temp_password`).
- `POST /api/v1/orgs/create/` and global-admin provisioning (Story 2.8) — creating an org auto-adds global admins as admins.

Verify these against the running backend and the Swagger UI rather than trusting this note verbatim (implementation may refine codes/messages).

### Scope / coordination

- API-contract docs only. User-journey narrative is **11.11**; architecture/permission model is **11.13**. The OpenAPI generator is the source of truth — reconcile prose to it, not the reverse.

### Project Structure Notes

- Docs under `docs/api/`. Schema/Swagger served by the backend (Story 11.9 — inspect `backend/` URL config for the schema/Swagger routes). Build gate: `pixi run docs-build`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 11.12]
- Epic 2 stories: `2-6` (auth/me, register), `2-7` (members by email), `2-8` (create-org/provisioning)
- Docs: `docs/api/authentication.md`, `docs/api/organizations.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
