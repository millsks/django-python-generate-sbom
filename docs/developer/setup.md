# Local Development

Local development is **containerless**: `pixi install`, then `pixi run dev`. There
is no Docker, PostgreSQL, Redis, or MinIO to run on your machine — the stack falls
back to SQLite, local-filesystem storage, and a filesystem Celery broker. This
works identically on **macOS** (osx-arm64) and **Windows** (win-64); Docker/Podman
are not required on either OS.

The [Docker Compose path](#running-the-prod-parity-stack-with-docker-compose)
remains documented below as the optional **prod-parity** stack — useful when you
want to exercise PostgreSQL, Redis, and S3-compatible storage locally — but the
containerless flow is the primary way to develop.

## Prerequisites

- [**pixi**](https://pixi.sh) — the single toolchain manager for the whole project.
  You do not need a separate `pip`, `conda`, or `uv` install step; pixi manages
  everything. There is no Node: the UI is server-rendered Django templates with
  vendored assets, so there is nothing to build. pixi resolves a native environment
  for your platform, so the same commands run on macOS and Windows.

That is the only hard prerequisite for containerless local dev. Docker + Docker
Compose are needed **only** for the optional prod-parity stack.

## First-time setup

```sh
pixi install          # resolve and install the environment
pixi run bootstrap    # install the pre-commit + commit-msg git hooks
```

Then create your local environment file from the containerless template:

```sh
cp .env.local.example .env    # copy on macOS/Linux; use `copy` on Windows cmd
```

`.env.local.example` is pre-wired for containerless dev: it sets
`DJANGO_SETTINGS_MODULE=config.settings.local` and deliberately leaves
`DATABASE_URL`, `AWS_*`, and `REDIS_URL` **unset** so the base defaults apply —
SQLite at `db.sqlite3` and `FileSystemStorage` at `media/`, both at the repository
root. `.env` is git-ignored; never commit secrets.

## Running the stack — `pixi run dev`

```sh
pixi run migrate      # apply database migrations (creates ./db.sqlite3)
pixi run dev          # start web + worker + beat together (containerless)
```

### A fresh database is required as of Story 21.2

Story 21.2 collapsed the four Django apps (`users`, `manifests`, `sbom`, `analysis`)
into a single `inventory` app and **rewrote migration history from scratch**. Django
identifies a model as `<app_label>.<ModelName>`, so changing the labels changed the
identity of every model, every foreign-key target, and every `ContentType` row — and the
tables moved with them (`users_org` is now `inventory_org`, `sbom_sbomjob` is now
`inventory_sbomjob`, and so on).

There is **no migration path** from a pre-21.2 database. Any local database created
before that story is unusable and must be recreated:

```sh
rm db.sqlite3                  # discard the pre-21.2 database (no upgrade path)
pixi run migrate               # rebuild the schema from the new initial migrations
pixi run seed-superuser        # recreate the superuser + ADMIN org (env-driven)
```

`seed-superuser` reads `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD`, and is
idempotent. The ADMIN org itself is seeded by the `inventory.0002_seed_admin_org` data
migration, so `pixi run migrate` alone is enough to get a working ADMIN org.

This was a deliberate, signed-off trade: at `version = 0.1.0` with nothing deployed, a
fresh database was judged far less risky than hand-authoring `SeparateDatabaseAndState`
state operations for ~10 models across four app labels plus a `ContentType` data
migration. The one thing that did **not** change is `AUTH_USER_MODEL`, which is still
`"users.User"` — the dissolved app freed the `users` label and `django_service.users`
re-took it.

`pixi run dev` runs [honcho](https://honcho.readthedocs.io) against the repo-root
`Procfile`, launching three processes in one foreground terminal:

| Process | Command | What it is |
|---|---|---|
| `web` | `pixi run runserver` | Django's `runserver` on `:8000` (not gunicorn) |
| `worker` | `pixi run worker` | A **real** Celery worker draining the `pipeline` + `analysis` queues |
| `beat` | `pixi run beat` | Celery Beat scheduler for maintenance jobs |

honcho is pure-Python and cross-platform, so this single command behaves the same
on macOS and Windows. `pixi run dev` sets `DJANGO_SETTINGS_MODULE=config.settings.local`
for the whole process tree, so no child process falls back to the
production-defaulting `wsgi.py`.

**Open the app at [http://localhost:8000](http://localhost:8000).** Django serves the
UI, the REST API, and static assets from that one port — there is no second dev server
and no build step. `runserver` reloads on Python changes, and template and static edits
are picked up on the next request.

> **Port conflict — `:8000`.** Both `pixi run dev` and the Docker Compose
> prod-parity stack bind port `:8000`. Do not run them at the same time — stop one
> before starting the other (`pixi run docker-down` to stop the Compose stack).

### Running pieces individually

You can also run each process in its own shell for finer control over reloads and
logs:

```sh
pixi run runserver          # Django runserver on :8000 (local settings)
pixi run worker             # Celery worker: pipeline + analysis queues
pixi run beat               # Celery Beat scheduler
pixi run flower             # Celery monitoring UI on :5555
```

See `pixi task list` for the full set.

## Windows specifics

The containerless flow is designed to run on Windows with no surprises, but a few
things differ from Unix:

- **Worker pool.** Celery's default **prefork** pool is Unix-only. On Windows
  (win-64) the `worker` task is overridden to run with `--pool=solo` — a
  single-threaded pool that is reliable for local development. macOS/Linux keep the
  prefork pool (`-c 4`). You do not configure this manually: pixi selects the
  right `worker` command for your platform automatically, so `pixi run dev` and
  `pixi run worker` are correct on both OSes.
- **`runserver`, not gunicorn.** gunicorn is a Unix-only WSGI server and is not
  installed on Windows. Local web always uses Django's `runserver` (cross-platform);
  gunicorn is used only on the containerized OCP/prod path.
- **Portable broker/beat paths.** The filesystem Celery broker and the Beat
  schedule live under a git-ignored `.celery/` tree at the repo root (broker messages
  under `.celery/broker/`, the Beat schedule at `.celery/celerybeat-schedule`). These
  paths are built with `pathlib`, so
  they are correct on Windows — nothing is written to POSIX-only `/tmp`, which does
  not exist there. The folders are created on import, so a fresh checkout can start
  a worker without a manual `mkdir`.

## Environment matrix — local vs. OCP/prod

Containerless local dev and the enterprise OCP/prod deployment diverge on every
backing service. The matrix below is the quick reference; see the
[OpenShift deployment guide](../deployment/openshift/index.md) for the full
prod topology and the
[migration guide](../deployment/openshift/migration-guide.md) for how the two map.

| Concern | Local (containerless) | OCP / production |
|---|---|---|
| **Settings module** | `config.settings.local` | `config.settings.production` |
| **Database** | SQLite (`db.sqlite3`) | Enterprise-managed **PostgreSQL** |
| **Object storage** | `FileSystemStorage` (`media/`) | Enterprise **S3**-compatible object storage |
| **Celery broker** | Kombu `filesystem://` (`.celery/broker/`) | Enterprise **Redis** |
| **Celery result backend** | `django-db` (results in SQLite) | Enterprise **Redis** |
| **Web server** | Django `runserver` | **gunicorn** |
| **Worker pool** | prefork (`-c 4`) on macOS/Linux, `--pool=solo` on Windows | prefork |
| **Containers** | None | Single umbrella image (Helm-deployed) |

Local dev needs **no Docker, PostgreSQL, Redis, or MinIO** — the base defaults are
the containerless defaults, and `config.settings.local` only swaps the Celery
transport (to the filesystem broker + `django-db` results) on top of them. The
OCP/prod side is driven by `config.settings.production` and is described in full in
the [OpenShift guide](../deployment/openshift/index.md).

## Running the prod-parity stack with Docker Compose

Docker Compose is the optional **prod-parity** path: it runs the app against real
PostgreSQL, Redis, and MinIO, so you can exercise the same backing services the
OCP/prod deployment uses. Reach for it when you need to reproduce a
storage/database/broker behavior that SQLite and the filesystem broker cannot, or
before a deployment. Everyday development does not need it — use `pixi run dev`.

This path **does** require Docker + Docker Compose installed locally.

```sh
pixi run docker-up      # build (if needed) and start all services in the background
pixi run docker-logs    # follow the logs
pixi run docker-down    # stop everything
```

The UI and the API are served by the `web` container (gunicorn); MinIO's
console and the Postgres/Redis ports are exposed for local inspection (see
`docker-compose.yml`). For migrations and management commands, run them inside the
`web` container:

```sh
pixi run docker-migrate     # apply migrations in the web container
pixi run docker-shell       # open a shell in the web container
```

## Creating the initial admin

Migrations seed the distinguished **ADMIN** org (`Org.is_admin_org=True`); members
of that org are **global admins** (see [Architecture](architecture.md)). There is no
auto-created "personal" org for the first user — a new account starts with zero
memberships. Instead, seed a Django **superuser**, which is automatically made a
global admin:

```sh
cd backend
python manage.py createsuperuser        # create_superuser hook → grant_global_admin
```

**Env-driven auto-seed (Story 2.13):** set `DJANGO_SUPERUSER_EMAIL` and
`DJANGO_SUPERUSER_PASSWORD` in `.env` and seeding creates that superuser (making
them a global admin via the `create_superuser` hook) if it does not already exist —
no manual step. The `.env.local.example` template ships placeholder values you can
edit. The command is idempotent: it skips cleanly when the vars are unset or the
user already exists, and never logs the password. You can also run it directly:

```sh
pixi run seed-superuser        # env-driven; idempotent (Story 2.13)
```

The seeded superuser is provisioned into the **ADMIN** org — there is no auto-created
personal org. Never commit real credentials.

`UserManager.create_superuser` calls `grant_global_admin`, so the new superuser is
written into the ADMIN org and back-filled as an admin of every org. If you created
superusers before running the seed migration (or need an idempotent catch-up), run:

```sh
cd backend
python manage.py bootstrap_admin_org    # ensure the ADMIN org exists; seed all superusers
```

Under Docker Compose, run these inside the `web` container (`pixi run docker-shell`,
then the same `python manage.py …` commands).

## Settings

Django settings are split under `src/config/settings/`:

| Module | Used for |
|---|---|
| `base.py` | Shared configuration (apps, DRF, Celery, storage, API-docs toggle); its SQLite + filesystem-storage defaults **are** the containerless defaults |
| `local.py` | Containerless local dev — the default `DJANGO_SETTINGS_MODULE` for `manage.py`, Celery, and pytest; swaps in the filesystem Celery broker + `django-db` results |
| `production.py` | Production hardening for the container/OCP path; the default for `wsgi.py`/`asgi.py` |

Configuration is environment-driven; never commit secrets or `.env` files.

## Everyday tasks

| Task | What it does |
|---|---|
| `pixi run dev` | Start the containerless stack (web + worker + beat) |
| `pixi run migrate` | Apply database migrations |
| `pixi run test` | Backend unit tests (fast) |
| `pixi run test-integration` | Backend integration tests |
| `pixi run cov` | Full backend suite with the ≥90% coverage gate |
| `pixi run fmt` / `pixi run lint` / `pixi run check` | Ruff format, Ruff lint, mypy |
| `pixi run docs-serve` | Live-preview this documentation site |
| `pixi run ci` | The full local gate — see [Testing](testing.md) |

Run `pixi task list` to see every available task.
