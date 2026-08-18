---
baseline_commit: 7897a91
---

# Story 21.2: Collapse Four Apps into `inventory` and Establish `django_service`

Status: review

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
   Given the 9 existing migrations span four app labels — `users` 0001–0004 (including the
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

- [x] **Task 0 — Obtain sign-off (AC: #6)** — Do not start until the fresh-database gate is explicitly
  approved. Record it.
- [x] **Task 1 — Establish `django_service.users` (AC: #2)** — Move the concrete `User` (and only the `User`)
  from the old `users` app to `src/django_service/users/`, keeping app label `users`. Add its `apps.py` with
  an explicit `label = "users"`.
- [x] **Task 2 — Collapse the four apps (AC: #1, #3, #4)** — Merge `users` (minus `User`), `manifests`, `sbom`,
  `analysis`, `common`, and `tasks` into `src/django_apps/inventory/` with an explicit
  `label = "inventory"` in `apps.py`. Keep every model class name.
- [x] **Task 3 — Decouple `User` references (AC: #2)** — Replace concrete-class imports with
  `settings.AUTH_USER_MODEL` in model FKs and `get_user_model()` at runtime. Add the no-import assertion test.
- [x] **Task 4 — Rewrite migrations (AC: #5)** — Delete the 9 existing migration files; generate one initial
  per app. Port the `0004_seed_admin_org` data migration into the `inventory` initial (or a `0002` data
  migration) so admin-org seeding still happens.
- [x] **Task 5 — Update settings + Celery (AC: #1, #8)** — `INSTALLED_APPS`, `REST_FRAMEWORK` dotted paths,
  `configure_structlog` import, `STORAGES` backend path, Celery `autodiscover`/task routes.
- [x] **Task 6 — Restructure `tests/` (AC: #8)** — Mirror the new module layout.
- [x] **Task 7 — Docs + gate (AC: #6, #7, #8)** — Update `docs/developer/setup.md`; verify the SPA end to end;
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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Sign-Off Record

**Fresh-database gate: SIGNED OFF by the product owner (Kevin Mills) on 2026-08-17.**
Approval given as "Signed off — proceed" in response to an explicit prompt stating what
would be destroyed. Evidence presented at sign-off time:

- **Nothing is deployed.** All eight Epic 19 stories (19-1..19-8) are `ready-for-dev`; none
  is implemented. (Correction to this story's stated evidence: the `epic-19` marker reads
  `in-progress`, not "entirely ready-for-dev" — but no story under it is done, so the
  conclusion stands.)
- `pyproject.toml` declares `version = "0.1.0"`.
- The local dev database was **not** empty and was knowingly discarded: 2 `users.User`,
  2 `Org`, 3 `OrgMembership`, 0 `OrgApiKey`, 2 `SBOMJob`, 2 `ManifestUpload`,
  6 `AnalysisReport`. The product owner declined a pre-flight backup.

### Debug Log References

- `pixi run ci` — **exit 0**. All 12 steps pass.
- Backend **429 passed** (421 unit + 8 integration), coverage **95.90%**. Frontend **223 passed**.
- `mypy src` clean over 84 files; `ruff check .` clean; `bandit -r src` 0 medium+.
- `manage.py makemigrations --check --dry-run` → **"No changes detected"** (AC #5, no drift).
- Migration run on a fresh DB: `users.0001_initial`, `inventory.0001_initial`,
  `inventory.0002_seed_admin_org` all OK, alongside `auth`, `admin`, `sessions`,
  `django_celery_results.0001..0011`, and `rest_framework_api_key.0001..0005`.
- App registry after the collapse:
  - `inventory` → label `inventory`, name `inventory`, models
    `[AnalysisReport, ManifestUpload, Org, OrgApiKey, OrgMembership, SBOMJob]`
  - `users` → label `users`, name `django_service.users`, models `[User]`
  - `manifests`, `sbom`, `analysis` → **gone**
  - `AUTH_USER_MODEL` → `users.User` (unchanged)
- Table moves confirmed: `inventory_org`, `inventory_orgmembership`, `inventory_orgapikey`,
  `inventory_manifestupload`, `inventory_sbomjob`, `inventory_analysisreport`.
- **Route-table parity (AC #7):** dumped the fully-resolved URL list at 21.1 and at 21.2 and
  diffed them — **byte-for-byte identical** (69 routes total, 30 under `/api/v1/`).
- **API-key parity (AD-8, the story's explicit warning):** `OrgApiKey.objects.create_key()`
  → `get_from_key()` roundtrip True after the table move; `Api-Key <raw>` → 200,
  no credentials → 401, bogus key → 401, session auth → 200.
- Session flow: register 201, login 200, `auth/me` 200 with payload
  `{"email", "id", "is_admin", "is_global_admin"}` (unchanged shape).
- Host→app seeding: `seed_superuser` creates `django_service.users.models.User`, and
  `grant_global_admin` puts them in the ADMIN org with role `admin`; `is_global_admin` True.
- Live server: SPA routes `/`, `/login`, `/register`, `/jobs`, `/organizations` → 200;
  `/health/` → 200; `/admin/` → 302 with `/admin/login/` rendering; `/api/docs/`,
  `/api/schema/` → 200.

### Completion Notes List

**Two corrections to the story's own stated facts.**
1. **Migration count.** AC #5 and Task 4 said "11 existing migrations"; the story's own
   enumeration lists **9**, and 9 is what was on disk (users 0001–0004, manifests
   0001–0002, sbom 0001, analysis 0001–0002). Corrected in the AC and task text above.
2. **Sign-off evidence.** The story asserted Epic 19 is "entirely `ready-for-dev`". The
   `epic-19` marker actually reads `in-progress`, though none of 19-1..19-8 is
   implemented, so the "nothing is deployed" conclusion stands. Recorded in the Sign-Off
   Record.

**AC #2 was the hard part, and the difficulty was mypy, not Django.** The app must not
name the host's concrete `User`, but the django-stubs plugin reads `AUTH_USER_MODEL` out
of the settings module and types every FK declared against it as the **concrete** class.
So annotating app code with `AbstractUser` produced **25 errors** at ORM boundaries
("Incompatible type for lookup 'user'", "Missing positional argument 'username'"). mypy is
right: a different host would have a different class, so from inside the app the static
type of "whatever the host's user FK accepts" is genuinely unknown.

Resolved with one seam module, `inventory/common/users.py`, which states that precisely
instead of hiding it:
- `UserT` (= `AbstractUser`) — the contract the app is allowed to assume of a user
  *instance*. Used in every app signature and cast, so app code stays fully type-checked.
- `user_model()` — the model class, for queries.
- `user_ref(user) -> Any` — adapts a user into an ORM field value or lookup. Looks like a
  no-op and is documented as deliberate: it marks the ~20 exact points where the concrete
  type is unknowable, rather than papering over them with per-line ignores or weakening
  every signature to `Any`.
- `create_user` / `create_superuser` — creation via an `_EmailUserManager` **Protocol**,
  because the app needs a manager that takes `email` first rather than Django's
  `username`. That requirement is now explicit and checkable instead of assumed.

Rejected: a `TYPE_CHECKING`-only import of the concrete `User`. It satisfies mypy with no
runtime coupling, but the app's *source* would still name `django_service.users.models`,
so the app could not drop into another platform without editing it — which is exactly what
AC #2 exists to prevent.

**Two queries were reaching through the HOST's reverse accessor.**
`_global_admins()` and `list_global_admins()` filtered
`user_model().objects.filter(org_memberships__org=...)`. `org_memberships` is a reverse
relation created by the app's own FK onto the *host's* class, so the app cannot assume it
exists. Both now query from `OrgMembership` (which the app owns) and read `.user`. This is
better code independent of the decoupling, and mypy flagged it as
"Cannot resolve keyword 'org_memberships'".

**A silent breakage the test suite could not have caught: management commands.**
Django discovers commands at `<app_module>/management/commands/`. Collapsing four apps into
`inventory` meant `inventory/users/management/` was no longer scanned, so `seed_superuser`
and `bootstrap_admin_org` **vanished** — `manage.py seed_superuser` returned
"Unknown command". The unit tests kept passing because they import and invoke the command
classes directly. Found by actually running `pixi run seed-superuser`. Both commands moved
to `src/django_apps/inventory/management/commands/`.

**Models live in subpackages, so `inventory/models.py` is load-bearing.** Django populates
the registry by importing exactly one module per app. The six model classes stay in their
domain subpackages (AC #1 keeps the file-role convention), so `inventory/models.py`
re-exports them. `app_label` then resolves to `inventory` automatically via
`apps.get_containing_app_config()` walking the defining module path — no `Meta.app_label`
anywhere. The trap this creates is documented in that module: **a model added to a
subpackage but not re-exported there is silently invisible to Django.**
`test_app_labels.py::test_inventory_owns_every_domain_model` fails if that happens.

**Four lazy label references had to be remapped** — easy to miss, and each would have
broken at import time: `OrgScopedModel.org` `"users.Org"` → `"inventory.Org"`,
`AnalysisReport.job` `"sbom.SBOMJob"` → `"inventory.SBOMJob"`, `SBOMJob.manifest`
`"manifests.ManifestUpload"` → `"inventory.ManifestUpload"`, and `OrgMembership.user`
`"users.User"` → `settings.AUTH_USER_MODEL`. The generated initial migration correctly
uses `migrations.swappable_dependency(settings.AUTH_USER_MODEL)`, so the app's migration
never names the host's label either.

**Migration generation order matters.** Running `makemigrations users inventory` in one
pass produced `inventory/0001_initial.py` **plus** `0002_initial.py`, because Django split
the FK wiring to break the app ordering. Generating `users` first and `inventory` second
yields a single initial per app, as AC #5 requires. The `0004_seed_admin_org` data
migration is ported as `inventory/0002_seed_admin_org.py` (sanctioned by Task 4), changed
only in its `get_model` label, and kept separate from `0001` so the data step stays
legible and independently reversible.

**The host's `User.create_superuser` imports the app on purpose.** It calls
`inventory.users.services.grant_global_admin` to seed the ADMIN org membership. That is
host → app, the allowed direction (the app never imports the host), and the import stays
deferred so it does not run while the registry is still populating. Verified end to end.

**Task 6 (restructure `tests/`) — judgment call, flagged for review.** `tests/unit/` is
flat and already keyed 1:1 to domains (`test_orgs`, `test_membership`, `test_apikeys`,
`test_manifests`, `test_sbom_*`, `test_analysis_*`, …), which mirrors the new subpackage
layout as well as it mirrored the old one. I did **not** reorganize the files into
`tests/unit/inventory/**`, because AC #7's parity proof is "existing API tests pass
unmodified except for import paths" and moving 40 files would bury that evidence in
rename noise. What changed in tests is exactly: the concrete-`User` import repointed to
`django_service.users.models` (11 files), `_ScopedThing.Meta.app_label` `"users"` →
`"inventory"`, and two new structural test modules. If you want the physical
reorganization, it is a clean standalone follow-up.

**`AUTH_USER_MODEL` never changed value**, so there is no swappable-model migration and no
third-party migration referencing the setting had to be reconciled — the single largest
risk reduction in this story, and `test_app_labels.py` now pins it.

**Not fixed here, as the story instructs:** the four deferred pluggability violations
(global DRF `DEFAULT_AUTHENTICATION_CLASSES` / `DEFAULT_PERMISSION_CLASSES`, `config`'s
`configure_structlog` import, the app-owned `STORAGES` backend). Also still open from
21.1: the `beat_schedule` maintenance tasks are not in the Celery registry — unchanged by
this story and still needing its own bug story.

### File List

**New (9)**
- `src/django_service/users/__init__.py`, `apps.py` (explicit `label = "users"`), `models.py`
  (concrete `User` + `UserManager`)
- `src/django_apps/inventory/apps.py` (`InventoryConfig`, `label = "inventory"`)
- `src/django_apps/inventory/models.py` (model registry / re-export)
- `src/django_apps/inventory/common/users.py` (the user seam)
- `src/django_apps/inventory/migrations/0001_initial.py`
- `tests/unit/test_app_labels.py` (AC #1/#2/#3)
- `tests/unit/test_app_user_decoupling.py` (AC #2, AST-based)

**Deleted (13)**
- The four sub-app configs: `{users,manifests,sbom,analysis}/apps.py`
- 8 of the 9 old migration files (the 9th, `0004_seed_admin_org`, was moved — see below)
- `users/management/commands/__init__.py`, `users/migrations/__init__.py`

**Moved (8)**
- `users/migrations/0001_initial.py` → `src/django_service/users/migrations/0001_initial.py`
- `users/migrations/0004_seed_admin_org.py` → `inventory/migrations/0002_seed_admin_org.py`
- `users/management/commands/{seed_superuser,bootstrap_admin_org}.py` →
  `inventory/management/commands/` (**required** for Django to find them again)
- package `__init__.py` files re-homed into the new `management/` and `migrations/` trees

**Modified — app (10)**
- `users/models.py` (concrete `User` removed; FK → `settings.AUTH_USER_MODEL`)
- `users/{services,views,auth,selectors,serializers}.py` (seam adoption; two reverse-relation
  queries rewritten onto `OrgMembership`)
- `{manifests,sbom}/services.py` (seam adoption)
- `common/models.py`, `analysis/models.py`, `sbom/models.py` (lazy label remap)

**Modified — project (4)**
- `src/config/settings/base.py` (`INSTALLED_APPS`: four entries → `django_service.users` +
  `inventory`)
- `docs/developer/setup.md` (AC #6: fresh-database requirement + recreation steps)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

**Modified — tests (12)**
- 11 files: concrete-`User` import → `django_service.users.models`
- `tests/unit/test_common_models.py`: `_ScopedThing.Meta.app_label` → `"inventory"`

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Collapsed the four Django apps (`users`, `manifests`, `sbom`, `analysis`) into a single `inventory` app and moved the concrete `User` to `django_service.users`, keeping the `users` label so `AUTH_USER_MODEL` is unchanged. Rewrote migration history to one initial per app plus a ported admin-org data migration; fresh database required (signed off). Added `inventory/common/users.py` as the app's only seam onto the host user model, so no app module imports the concrete class. Route table verified byte-identical to 21.1 and the API-key path verified end to end. `pixi run ci` exit 0; 429 backend tests at 95.90%, 223 frontend. |
