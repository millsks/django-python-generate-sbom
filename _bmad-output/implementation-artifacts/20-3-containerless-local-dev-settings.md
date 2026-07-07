# Story 20.3: Containerless Local Dev Settings

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 20.2**. This story establishes the Django settings module that the
> cross-platform worker (20.4) and the `pixi run dev` runner (20.5) both point at.

## Story

As a developer,
I want a local dev settings module that uses SQLite, filesystem storage, and a containerless Celery config,
so that the whole stack runs on macOS or Windows with no Postgres, Redis, MinIO, or Docker.

## Acceptance Criteria

1. **SQLite + filesystem storage confirmed as the local defaults.**
   Given `backend/config/settings/base.py` already defaults `DATABASES` to
   `sqlite:///{BASE_DIR}/db.sqlite3` when `DATABASE_URL` is unset (L108–110) and `STORAGES["default"]` to
   `FileSystemStorage` with `MEDIA_ROOT = BASE_DIR / "media"` (L130–137), when the local dev settings load with
   no `DATABASE_URL`/`AWS_*` env, then the app uses `backend/db.sqlite3` and `backend/media/` — **no DB or
   object-storage rewrite is required**; the settings module only needs to *not* re-introduce Postgres/S3.
2. **A local dev settings module exists and is containerless.**
   Given `config.settings.local` exists (9 lines: `DEBUG=True`, adds `0.0.0.0` to `ALLOWED_HOSTS`, console
   logs — no infra swaps), when this story lands, then the local dev settings module (extend `local.py` or add
   a sibling) inherits the SQLite + filesystem + console-log defaults and hosts the containerless Celery
   configuration (delegated to Story 20.4), so a single `DJANGO_SETTINGS_MODULE` value gives a fully
   container-free local app.
3. **All local entry points resolve to the local settings.**
   Given `manage.py` (L10), `config/celery_app.py` (L14), and pytest (`pyproject.toml` L18) already default to
   `config.settings.local`, while `wsgi.py`/`asgi.py` default to `config.settings.production` (L6), when local
   dev runs, then every containerless local process (`runserver`, the worker, beat, tests) uses the local
   settings module — the production-defaulting `wsgi`/`asgi` are used only by the container/prod `web` task
   (gunicorn), which is out of scope for containerless local dev.
4. **A containerless `.env.example` is provided.**
   Given the existing `.env.example` targets the container stack
   (`DJANGO_SETTINGS_MODULE=config.settings.production`, `DATABASE_URL=postgres://…@postgres:5432/…`,
   `REDIS_URL=redis://redis:6379/0`), when this story lands, then a containerless example env
   (`.env.local.example`, or a documented section) sets `DJANGO_SETTINGS_MODULE=config.settings.local`, leaves
   `DATABASE_URL`/`AWS_*`/`REDIS_URL` **unset** (so the SQLite/filesystem defaults apply), and documents the
   local Celery filesystem transport vars introduced in Story 20.4 — with no Postgres/Redis/MinIO endpoints.
5. **Tests + gate green.**
   Given the settings change, when `pixi run ci` runs, then it is green with a test asserting the local dev
   settings resolve to SQLite (`DATABASES["default"]["ENGINE"]` is sqlite) and `FileSystemStorage`, and no
   Postgres/S3 is configured under the local module.

## Tasks / Subtasks

- [ ] **Task 1 — Local dev settings module (AC: #1, #2)** — Extend `config/settings/local.py` (or add a
  documented sibling) so it inherits the SQLite + filesystem + console-log base defaults and provides the home
  for the Story 20.4 Celery block. Do **not** define a `DATABASES`/`STORAGES` swap — the base defaults are the
  containerless defaults.
- [ ] **Task 2 — Entry-point audit (AC: #3)** — Confirm `manage.py`, `celery_app.py`, and pytest resolve to
  `config.settings.local`; document that `wsgi`/`asgi` (production-defaulting) belong to the container/prod
  path only.
- [ ] **Task 3 — Containerless env example (AC: #4)** — Add `.env.local.example` (or a clearly separated
  section) with `DJANGO_SETTINGS_MODULE=config.settings.local`, no DB/S3/Redis endpoints, and placeholders for
  the local Celery filesystem vars from 20.4.
- [ ] **Task 4 — Test + gate (AC: #5)** — Add a settings test asserting SQLite + FileSystemStorage under the
  local module; run `pixi run ci` to green (coverage ≥90%).

## Dev Notes

### Grounded facts (verified)

- `base.py` L108–110: `DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}`
  — SQLite by default (`BASE_DIR` = `backend/`, L15).
- `base.py` L130–137: `STORAGES["default"] = FileSystemStorage`, `MEDIA_ROOT = BASE_DIR / "media"`;
  `staticfiles` = WhiteNoise.
- `base.py` L147–158: Celery broker + result backend both = `REDIS_URL` (default `redis://localhost:6379/0`);
  `CELERY_TASK_DEFAULT_QUEUE = "pipeline"`; soft/hard limits 1800/2100s. Story 20.4 replaces the transport for
  local; this story only establishes where that config lives.
- Settings modules today: `base.py` (189L, shared), `local.py` (9L, `DEBUG`/`0.0.0.0`/console — no swaps),
  `production.py` (45L, swaps `REQUESTS_CACHE_BACKEND=redis` L25 and S3 storage L38–44; Postgres comes purely
  from `DATABASE_URL` env, not a hardcoded block). There is **no** `dev.py` / `test.py`.
- `DJANGO_SETTINGS_MODULE` defaults: `manage.py` L10 = local; `celery_app.py` L14 = local; `pyproject.toml`
  pytest L18 = local; `wsgi.py`/`asgi.py` L6 = production; `.env.example` L7 = production.

### Decision — reuse `local.py`

`local.py` already *is* the containerless local module (SQLite + filesystem inherited from base; no infra
swap). Prefer extending it over introducing a new module, so the many entry points already defaulting to
`config.settings.local` need no change. The only additions are the Story 20.4 Celery block and the env example.

### Testing standards

- Unit test under `backend/tests/unit/` asserting the resolved `DATABASES`/`STORAGES` under the local settings
  are SQLite + FileSystemStorage (no network/DB — pure settings introspection).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.3: Containerless Local Dev Settings]
- `backend/config/settings/base.py` (L108–110 DB, L130–137 storage, L147–158 Celery),
  `backend/config/settings/local.py`, `backend/config/settings/production.py`.
- `backend/manage.py` (L10), `backend/config/{wsgi,asgi,celery_app}.py`, `backend/pyproject.toml` (L18),
  `.env.example`.
- Downstream: `20-4-cross-platform-async-worker.md` (fills the Celery block),
  `20-5-cross-platform-pixi-tasks-and-dev-runner.md` (tasks set `DJANGO_SETTINGS_MODULE=config.settings.local`).

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
