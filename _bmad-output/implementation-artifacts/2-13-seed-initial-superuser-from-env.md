# Story 2.13: Seed the Initial Superuser from Environment Variables (Bugfix)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want the initial superuser (global admin) seeded automatically from environment variables,
so that a fresh stack comes up with a global admin without a manual `createsuperuser` step.

## Acceptance Criteria

1. **Env-driven seed on startup.** When `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` are set, an idempotent startup step creates that superuser (if absent) via `createsuperuser --noinput` (or an equivalent management command). The `create_superuser` hook (Story 2.8) then makes them a **global admin** (ADMIN-org member).
2. **Idempotent / safe to re-run.** If the superuser already exists, or the env vars are unset, seeding is skipped cleanly — no error, no duplicate — so it's safe on every container boot.
3. **Wired into compose + documented.** The `web` service runs the seed step after `migrate` and before `web`. `DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD` are documented in `.env.example`/README as a dev convenience (never commit real credentials). Covered by a test.

## Tasks / Subtasks

- [ ] **Task 1 — Seed mechanism (AC: #1, #2)**
  - [ ] Add an idempotent seed. Recommended: a management command `seed_superuser` that — when `DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD` are set and no user with that email exists — calls `User.objects.create_superuser(email, password)` (which triggers `grant_global_admin`). Skip (structlog info + return) when the vars are unset or the user already exists. (Wrapping Django's `createsuperuser --noinput` also works — it reads `DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD`; `USERNAME_FIELD=email`, `REQUIRED_FIELDS=[]` — but a custom command gives cleaner idempotency + logging.)
  - [ ] Must run AFTER migrations (the ADMIN org is created by data migration `0004_seed_admin_org`, required by `grant_global_admin`).
- [ ] **Task 2 — Compose wiring (AC: #3)**
  - [ ] `docker-compose.yml` `web` service `command`: `sh -c "pixi run migrate && pixi run python backend/manage.py seed_superuser && pixi run web"` (or a dedicated pixi task). No-op when the env vars are unset.
  - [ ] Add `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD` to the `web` service environment and to `.env.example` with placeholder values + a "dev only — never commit real credentials" note.
- [ ] **Task 3 — Docs (AC: #3)**
  - [ ] Update `README.md` / `docs/developer/setup.md`: a fresh stack auto-seeds a global admin from these env vars; the manual `createsuperuser` path remains supported. (Small edits — coordinate with any in-flight Epic 11 doc reconciliation.)
- [ ] **Task 4 — Tests (AC: #1, #2)**
  - [ ] `call_command("seed_superuser")` with env set → superuser created and is a global admin (ADMIN-org member); run again → no duplicate/error; env unset → no user created.

## Dev Notes

- The email-based `User` has `USERNAME_FIELD="email"`, `REQUIRED_FIELDS=[]` (`backend/generate_sbom/users/models.py`), so `createsuperuser --noinput` needs only `DJANGO_SUPERUSER_EMAIL` + `DJANGO_SUPERUSER_PASSWORD`.
- `create_superuser` (`models.py:49`) calls `services.grant_global_admin`, which requires the ADMIN org (data migration `0004_seed_admin_org`) — so seed after `migrate`. `bootstrap_admin_org` already exists for pre-existing superusers; this story adds the **env-driven, automatic** path.
- Never log the password; never commit real credentials — `.env` is gitignored, so only `.env.example` gets placeholders.
- No new runtime dependency; no migration.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.13: Seed the Initial Superuser from Environment Variables (Bugfix)]
- Backend: `backend/generate_sbom/users/models.py:33` (`create_superuser` → `grant_global_admin`), `management/commands/bootstrap_admin_org.py`, migration `0004_seed_admin_org.py`
- Ops: `docker-compose.yml` (`web` service `command`), `README.md:126-133`, `docs/developer/setup.md`
- Related: `2-8-global-admin-org-and-cross-org-provisioning.md`, `2-12-restrict-org-creation-to-global-admins.md`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
