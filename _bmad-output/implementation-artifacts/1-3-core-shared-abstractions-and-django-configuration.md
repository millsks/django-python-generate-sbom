# Story 1.3: Core Shared Abstractions & Django Configuration

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want core Django configuration and shared base classes in place,
so that all feature apps can be built consistently on top of them without re-deciding foundational patterns.

## Acceptance Criteria

1. Given `OrgScopedModel` defined as an abstract Django model, when any app's `models.py` extends it, then the concrete model automatically receives an `org` FK to `Org` and the `OrgScopedQuerySet` default manager with a `.for_org(org)` method — no migration is generated for the abstract base itself.
2. Given `OrgScopedQuerySet.for_org(org)`, when called on any queryset derived from `OrgScopedModel`, then it returns only records where `org` matches the supplied org; records from other orgs are excluded.
3. Given `structlog` configured in `backend/config/settings/base.py`, when any module calls `structlog.get_logger().info("event", key="value")`, then the log output is a single JSON line containing the event name and the key-value pair; no `print()` or stdlib `logging` calls appear anywhere in the codebase.
4. Given `django-environ` configured in `backend/config/settings/base.py`, when `DATABASE_URL`, `REDIS_URL`, and `AWS_*` / MinIO vars are present in the environment, then Django connects to PostgreSQL, Celery connects to Redis, and `django-storages` connects to MinIO without any hardcoded values.
5. Given `backend/config/celery_app.py`, when a Celery worker starts with `celery -A config.celery_app worker`, then it connects to the Redis broker and the app is discoverable; all future task modules decorated with `@shared_task` will be auto-discovered.
6. Given `backend/config/settings/` containing `base.py`, `local.py`, and `production.py`, when `DJANGO_SETTINGS_MODULE` is set to `config.settings.local`, then Django starts without error, `DEBUG=True`, and uses the local database and Redis URLs.
7. Given unit tests covering `OrgScopedModel` and `OrgScopedQuerySet`, when `pixi run cov` runs, then coverage on the affected modules is ≥90% and `pixi run ci` exits 0.

## Tasks / Subtasks

- [ ] Task 1 — Minimal `Org` model to anchor the FK (AC: #1, #2)
  - [ ] `OrgScopedModel` needs a concrete `Org` to point its FK at. Create a minimal `users/models.py` `Org` (name, slug, created_at) — just enough to satisfy the FK; full user/org behavior is Epic 2 Story 2.1
  - [ ] Generate the initial migration for `Org`
  - [ ] Note for Story 2.1: it extends this `Org`, it does not recreate it
- [ ] Task 2 — `OrgScopedModel` + `OrgScopedQuerySet` abstract base (AC: #1, #2)
  - [ ] Place in a shared location (e.g. `<project_slug>/common/models.py`) importable by all apps without creating cross-app dependencies (AD-1)
  - [ ] `OrgScopedQuerySet(models.QuerySet)` with `def for_org(self, org)` → `self.filter(org=org)`
  - [ ] `OrgScopedManager = models.Manager.from_queryset(OrgScopedQuerySet)`
  - [ ] `OrgScopedModel(models.Model)`: `org = ForeignKey(Org, on_delete=CASCADE, related_name='+')`, `objects = OrgScopedManager()`, `class Meta: abstract = True`
  - [ ] Confirm `makemigrations` produces NO migration for the abstract base itself (AC #1)
- [ ] Task 3 — Settings split (AC: #4, #6)
  - [ ] `config/settings/base.py`: shared settings, INSTALLED_APPS, MIDDLEWARE (incl. WhiteNoise), DRF config, django-environ `env = environ.Env()` reading `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `REDIS_URL`, `AWS_*`, `SBOM_*`, `CELERY_*`
  - [ ] `config/settings/local.py`: `DEBUG=True`, WhiteNoise, console email, MinIO endpoint, `ConsoleRenderer` acceptable for structlog
  - [ ] `config/settings/production.py`: gunicorn-oriented, S3, HTTPS/security headers, `JSONRenderer`
  - [ ] DB via `env.db('DATABASE_URL')`; cache/broker via `REDIS_URL`; default file storage via `django-storages` S3Boto3Storage using `AWS_*` + `AWS_S3_ENDPOINT_URL`
- [ ] Task 4 — structlog configuration (AC: #3)
  - [ ] Configure structlog in `base.py` with processors ending in `JSONRenderer` (production) — key=value/JSON so logs are aggregator-parseable
  - [ ] Establish the convention that every log entry binds `org_id`, `task_id` (where applicable), `user_id` (NFR-5.3); provide a helper/bound-logger pattern later stories reuse
  - [ ] Exclude `Authorization` headers from any request logging
  - [ ] Add a lint/CI guard or documented rule: no `print()`, no stdlib `logging`
- [ ] Task 5 — Celery app (AC: #5)
  - [ ] `config/celery_app.py`: create the Celery app, `config_from_object('django.conf:settings', namespace='CELERY')`, `autodiscover_tasks()`
  - [ ] Define the two queues `pipeline` and `analysis` and task routing scaffolding (AD-4) — routes filled per-task in later epics, but the queue names and default routing live here
  - [ ] Wire soft/hard time limits from `CELERY_TASK_SOFT_TIME_LIMIT` / `CELERY_TASK_TIME_LIMIT`
  - [ ] Beat schedule dict present (empty or with the cleanup placeholder) — the cleanup task itself is Epic 7
- [ ] Task 6 — Tests (AC: #7)
  - [ ] Unit tests: `OrgScopedQuerySet.for_org(org)` returns only matching-org rows using a throwaway concrete test model or the `Org` FK on a real scoped model
  - [ ] Test that structlog emits a single JSON line with the event + bound keys (capture via `structlog` testing utilities / `capsys`)
  - [ ] Test that `DJANGO_SETTINGS_MODULE=config.settings.local` imports and `DEBUG is True`
  - [ ] Ensure ≥90% coverage on `common/models.py` and the settings/logging helpers touched

## Dev Notes

### `OrgScopedModel` is the load-bearing multi-tenancy primitive (AD-2)

Reference implementation shape:

```python
# <project_slug>/common/models.py
from django.db import models

class OrgScopedQuerySet(models.QuerySet):
    def for_org(self, org):
        return self.filter(org=org)

OrgScopedManager = models.Manager.from_queryset(OrgScopedQuerySet)

class OrgScopedModel(models.Model):
    org = models.ForeignKey("users.Org", on_delete=models.CASCADE, related_name="+")
    objects = OrgScopedManager()

    class Meta:
        abstract = True
```

Every model owning org data (`ManifestUpload`, `SBOMJob`, …) extends this. Every service/selector takes `org` as its first positional argument. API views read `org = request.auth.org` and pass it through. API endpoints return `404` on cross-org access (queryset returns no row); web UI routes return `403`. This is the single most important invariant in the system — get the `.for_org()` semantics exactly right and covered.

### Why `Org` is created here, minimally (dependency note)

`OrgScopedModel`'s FK needs a concrete `Org`. Rather than a forward dependency on Epic 2, this story creates a **minimal** `Org` (name, slug, created_at) to anchor the FK. Story 2.1 extends the same `users.Org` with membership/registration behavior — it must NOT redefine the model. This keeps Epic 1 self-contained and Story 2.1 additive. [Source: solution-design.md § 3.1]

### structlog configuration (NFR-5.3, global standard §2)

- JSON (production) / key=value renderer so logs are machine-parseable without heuristics.
- Bind `org_id`, `task_id`, `user_id` on every entry where applicable.
- Never `print()`, never stdlib `logging` — anywhere, including tests and scripts.
- Never log `Authorization` headers or secrets.

### django-environ + settings (solution-design.md § 8)

All runtime config via env vars; no committed secrets. Key reads: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `REDIS_URL`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `SBOM_MAX_CONCURRENT_JOBS_PER_ORG` (default 5), `SBOM_LTS_REGISTRY`, `CELERY_TASK_SOFT_TIME_LIMIT` (1800), `CELERY_TASK_TIME_LIMIT` (2100).

### Celery app (AD-4, AD-10; solution-design.md § 4)

- `@shared_task` everywhere — no Celery app import in task modules (enforced from here on).
- Two queues: `pipeline` (phases 1–3, 8, + Beat cleanup) and `analysis` (phases 4–7). This story establishes the queue names and the app; task definitions and routes come with their epics.
- `delay_on_commit()` is the mandated dispatch mechanism from views (AD-10) — document it in the Celery module docstring so later stories follow it.
- Beat schedule placeholder only; the `expire_artifacts_task` is Epic 7. [Source: solution-design.md § 4.5]

### Testing standards

- Unit tests must not hit real network/DB beyond Django's test DB; `for_org` isolation is the critical case (create rows in two orgs, assert `.for_org(a)` excludes b).
- structlog output assertion: configure a capturing processor or use `structlog.testing.capture_logs`.
- ≥90% coverage gate via `pixi run cov`.

### Constraints / guardrails

- AD-1: `common/` must not import from feature apps; feature apps import from `common/`, not vice versa. `users/` is the base layer.
- Do not put business logic in `models.py` (file-roles convention: models = ORM only).
- The abstract base must produce no migration (verify with `makemigrations --check`).

### Project Structure Notes

- Shared base classes live under `<project_slug>/common/` (new, small) — importable by all apps without creating cross-app coupling (satisfies AD-1's dependency direction; `common/` sits below `users/` or beside it as a leaf with no app imports).
- `config/settings/`, `config/celery_app.py`, `config/urls.py` are populated/extended here; `config/urls.py` already carries `/health/` from Story 1.2.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3: Core Shared Abstractions & Django Configuration]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: ARCHITECTURE-SPINE.md#AD-1 — Modular monolith]
- [Source: ARCHITECTURE-SPINE.md#AD-4 — Two Celery queues]
- [Source: ARCHITECTURE-SPINE.md#AD-10 — delay_on_commit]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Logging, Configuration]
- [Source: solution-design.md#3.1 users/ — Org model]
- [Source: solution-design.md#4. Celery Pipeline]
- [Source: solution-design.md#8. Configuration]
- [Source: solution-design.md#11. Observability]
- [Source: prd.md#NFR-5.2, NFR-5.3]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
