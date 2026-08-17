# Story 21.2: Collapse Four Apps into `inventory` and Establish `django_service`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.1**. 21.1 puts the tree in place mechanically; this story changes app
> labels and rewrites migration history. **The largest and riskiest story in Epic 21.**

> **⚠ SIGN-OFF GATE.** This story rewrites migration history and **requires a fresh database**. The product
> owner must confirm at implementation time that no environment holds data worth preserving. Evidence that
> none does: Epic 19 (OpenShift) is entirely `ready-for-dev` — stories 19-1..19-8 unimplemented, so nothing is
> deployed — and `pyproject.toml` declares `version = "0.1.0"`. Do not begin without recorded sign-off.

## Story

As a developer,
I want the four Django apps merged into one `inventory` app with the concrete `User` model owned by
`src/django_service/users/`,
so that the project ships a single cohesive app that references `settings.AUTH_USER_MODEL` rather than owning
user identity itself.

## Acceptance Criteria

1. **The four app labels collapse into one.**
   Given `INSTALLED_APPS` (`base.py:38-41`) lists `generate_sbom.users`, `.manifests`, `.sbom`, and
   `.analysis`, when they are collapsed, then a single `inventory` app remains at `src/django_apps/inventory/`
   — installed as `"inventory"`, unqualified — with the former four apps plus `common` and `tasks` as
   submodules, organised so the established file-role convention still holds (`views.py` = DRF views only,
   `services.py` = mutations, `selectors.py` = read-only queries, `models.py` = ORM only).
2. **`django_service` owns the concrete `User`, and `AUTH_USER_MODEL` does not change.**
   Given collapsing the old `users` app frees the `users` label, when the host package is established, then
   `src/django_service/users/` holds the concrete email-login `User` under the **same** `users` label, so
   `AUTH_USER_MODEL = "users.User"` (`base.py:44`) is **unchanged** as a string, and **no** module inside
   `src/django_apps/inventory/` imports the concrete `User` class — every reference goes through
   `settings.AUTH_USER_MODEL` (model FKs) or `get_user_model()` (runtime). A test asserts the absence of any
   such import.
3. **Domain models keep their names (no L2 rename).**
   Given the rename is of the *app*, not the *domain*, when the collapse lands, then `SBOMJob`,
   `ManifestUpload`, `AnalysisReport`, `Org`, `OrgMembership`, and `OrgApiKey` all keep their class names,
   `OrgApiKey` still extends `AbstractAPIKey` (**AD-8** intact), and no DRF serializer field name changes.
4. **Org models stay in the app.**
   Given `Org`, `OrgMembership`, and `OrgApiKey` are domain models the app owns, when the split lands, then all
   three remain inside `inventory` with their `User` FKs pointing at `settings.AUTH_USER_MODEL`, and
   `OrgScopedModel`/`OrgScopedQuerySet` (**AD-2**) continue to work unchanged.
5. **Migration history is rewritten to a single initial set per app.**
   Given the 11 existing migrations span four app labels — `users` 0001–0004 (including the
   `0004_seed_admin_org` **data** migration), `manifests` 0001–0002, `sbom` 0001, `analysis` 0001–0002 — when
   history is rewritten, then `src/django_apps/inventory/migrations/0001_initial.py` and
   `src/django_service/users/migrations/0001_initial.py` are the only migration files, the admin-org seeding
   behaviour from `0004_seed_admin_org` is preserved, and `manage.py makemigrations --check --dry-run` reports
   no drift.
6. **The fresh-database requirement is documented and signed off.**
   Given existing developer databases become unusable, when the story lands, then `docs/developer/setup.md`
   documents that a fresh database is required and how to recreate it (drop `db.sqlite3`, `pixi run migrate`,
   `pixi run seed-superuser`), and the product owner's sign-off is recorded in this story's Dev Agent Record.
7. **The API is byte-identical.**
   Given every import path and every test changes, when the story completes, then `/api/v1/` responds
   identically — no URL, payload, or status-code change on any of the 21 `users` routes or the
   manifests/sbom/analysis routes — and the React SPA still functions unchanged against it.
8. **Gate green.**
   Given the restructure touches every module, when `pixi run ci` runs, then it exits 0 with coverage ≥90%,
   `tests/` mirrors the new structure, and the Celery task routing (**AD-4**: `pipeline` and `analysis`
   queues) still resolves after the module moves.

## Tasks / Subtasks

- [ ] **Task 0 — Obtain sign-off (AC: #6)** — Do not start until the fresh-database gate is explicitly
  approved. Record it.
- [ ] **Task 1 — Establish `django_service.users` (AC: #2)** — Move the concrete `User` (and only the `User`)
  from the old `users` app to `src/django_service/users/`, keeping app label `users`. Add its `apps.py` with
  an explicit `label = "users"`.
- [ ] **Task 2 — Collapse the four apps (AC: #1, #3, #4)** — Merge `users` (minus `User`), `manifests`, `sbom`,
  `analysis`, `common`, and `tasks` into `src/django_apps/inventory/` with an explicit
  `label = "inventory"` in `apps.py`. Keep every model class name.
- [ ] **Task 3 — Decouple `User` references (AC: #2)** — Replace concrete-class imports with
  `settings.AUTH_USER_MODEL` in model FKs and `get_user_model()` at runtime. Add the no-import assertion test.
- [ ] **Task 4 — Rewrite migrations (AC: #5)** — Delete the 11 existing migration files; generate one initial
  per app. Port the `0004_seed_admin_org` data migration into the `inventory` initial (or a `0002` data
  migration) so admin-org seeding still happens.
- [ ] **Task 5 — Update settings + Celery (AC: #1, #8)** — `INSTALLED_APPS`, `REST_FRAMEWORK` dotted paths,
  `configure_structlog` import, `STORAGES` backend path, Celery `autodiscover`/task routes.
- [ ] **Task 6 — Restructure `tests/` (AC: #8)** — Mirror the new module layout.
- [ ] **Task 7 — Docs + gate (AC: #6, #7, #8)** — Update `docs/developer/setup.md`; verify the SPA end to end;
  `pixi run ci` to green.

## Dev Notes

### Grounded facts (verified)

- `backend/config/settings/base.py`: `INSTALLED_APPS` L23 (the four app entries L38–41), `AUTH_USER_MODEL` L44,
  `REST_FRAMEWORK` L46–58 (auth classes L52–53, permission class L55), `configure_structlog` import L12.
- `backend/config/settings/production.py:42`: `STORAGES["default"]` = `generate_sbom.common.storage.PublicEndpointS3Storage`.
- Migration files (11): `users/0001_initial`, `0002_orgapikey`, `0003_org_is_admin_org`,
  `0004_seed_admin_org` (**data**); `manifests/0001_initial`, `0002_alter_manifestupload_user`;
  `sbom/0001_initial`; `analysis/0001_initial`, `0002_alter_analysisreport_report_type`.
- App modules today: `users/` (11 py files incl. `auth.py`, `authentication.py`, `schema.py`, `selectors.py`,
  `services.py`, `serializers.py`, `views.py`, `urls.py`, management commands), `manifests/` (8),
  `sbom/` (10 + `parsers/` 9), `analysis/` (5 + `services/` 7), `common/` (7), `tasks/` (4).
- `users/urls.py` exposes **21** routes under `/api/v1/`.

### The label collapse is a migration rewrite, not a rename

Django identifies a model as `<app_label>.<ModelName>`. Changing four labels to one changes the identity of
every model, every FK target, and every `ContentType` row. `SeparateDatabaseAndState` could in principle
preserve an existing database, but it would require hand-authored state operations for ~10 models across four
apps plus a `ContentType` data migration — far more risk than a fresh database carries at v0.1.0 with nothing
deployed. Hence the squash, and hence the gate.

### `AUTH_USER_MODEL` stays `"users.User"` — deliberately

The old `users` app is being dissolved, which frees the label. Re-taking it in `django_service` means the
setting's *value* never changes, so no `AUTH_USER_MODEL` swap migration is needed and no third-party migration
referencing `settings.AUTH_USER_MODEL` has to be reconciled. This is the single largest risk reduction
available in this story — do not "tidy" the label to `accounts`.

### Watch for

- **`django-celery-results`** (added in Story 20.4) has its own migrations; they are unaffected but the fresh
  database must run them too.
- **`rest_framework_api_key`** migrations back `AbstractAPIKey`. `OrgApiKey` moving app labels means its table
  moves — verify key authentication end to end after the squash, not just at import time.
- **`ContentType` / `Permission` rows** referencing the old labels vanish with the fresh database. Any code
  or fixture referencing a permission by `app_label` needs updating.
- **Do not fix the four pluggability violations here** (global DRF keys, `config`'s `configure_structlog`
  import, the app-owned `STORAGES` backend). They are deliberately deferred — see the Epic 21 preamble.

### Testing standards

- A unit test asserting no module under `src/django_apps/inventory/` imports the concrete `User` class.
- A test asserting `apps.get_app_config("inventory").label == "inventory"` and that the four old labels are
  absent.
- Existing API tests must pass **unmodified except for import paths** — that is the parity proof for AC #7.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.2: Collapse Four Apps into `inventory` and Establish `django_service`]
- `backend/config/settings/base.py`, `backend/generate_sbom/**`, all 11 migration files.
- Upstream: `21-1-restructure-to-src-layout.md`. Downstream: every remaining Epic 21 story.
- Architecture: AD-2 (org scoping), AD-3 (service purity), AD-8 (API key), AD-16/AD-17 (new, recorded in 21.20).

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Sign-Off Record

_(fresh-database gate — record the product owner's approval here before starting)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
