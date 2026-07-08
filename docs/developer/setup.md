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

- [**pixi**](https://pixi.sh) — the single toolchain manager for the whole project
  (Python **and** Node). You do not need a separate `pip`, `conda`, `nvm`, or `npm`
  install step; pixi manages all of them. pixi resolves a native environment for
  your platform, so the same commands run on macOS and Windows.

That is the only hard prerequisite for containerless local dev. Docker + Docker
Compose are needed **only** for the optional prod-parity stack.

## First-time setup

```sh
pixi install          # resolve and install the full environment (Python + Node)
pixi run bootstrap    # install the pre-commit + commit-msg git hooks
```

Then create your local environment file from the containerless template:

```sh
cp .env.local.example .env    # copy on macOS/Linux; use `copy` on Windows cmd
```

`.env.local.example` is pre-wired for containerless dev: it sets
`DJANGO_SETTINGS_MODULE=config.settings.local` and deliberately leaves
`DATABASE_URL`, `AWS_*`, and `REDIS_URL` **unset** so the base defaults apply —
SQLite at `backend/db.sqlite3` and `FileSystemStorage` at `backend/media/`. `.env`
is git-ignored; never commit secrets.

## Running the stack — `pixi run dev`

```sh
pixi run migrate      # apply database migrations (creates backend/db.sqlite3)
pixi run dev          # start web + worker + beat together (containerless)
```

`pixi run dev` runs [honcho](https://honcho.readthedocs.io) against the repo-root
`Procfile`, launching four processes in one foreground terminal:

| Process | Command | What it is |
|---|---|---|
| `web` | `pixi run runserver` | Django's `runserver` on `:8000` (not gunicorn) |
| `worker` | `pixi run worker` | A **real** Celery worker draining the `pipeline` + `analysis` queues |
| `beat` | `pixi run beat` | Celery Beat scheduler for maintenance jobs |
| `frontend` | `pixi run fe-dev` | The Vite HMR dev server on `:5173`, proxying `/api` to Django on `:8000` |

honcho is pure-Python and cross-platform, so this single command behaves the same
on macOS and Windows. `pixi run dev` sets `DJANGO_SETTINGS_MODULE=config.settings.local`
for the whole process tree, so no child process falls back to the
production-defaulting `wsgi.py`.

**Open the app at [http://localhost:5173](http://localhost:5173)** — the Vite dev
server serves the hot-reloading UI and proxies `/api` (and `/admin`, `/static`) to
Django on `:8000`, so the SPA's API calls reach the real backend. Editing a file
under `frontend/src/` reloads instantly with no rebuild. (The Django server on
`:8000` serves the API directly; it only serves the built SPA from `frontend/dist/`
when you have run `pixi run fe-build` — the dev server on `:5173` is the primary UI
during development.)

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
pixi run fe-dev             # Vite HMR dev server on :5173 (proxies /api → :8000)
```

`pixi run fe-dev` runs the frontend on its own — useful when the backend is already
up (via `pixi run dev`, a container, or the individual tasks above) and you only
want to iterate on the UI. Other frontend tasks (`fe-build`, `fe-lint`, `fe-test`,
`fe-typecheck`, …) run through their own `fe-*` pixi tasks; see `pixi task list`.

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
- **Frontend dev server.** `pixi run fe-dev` (and the `frontend` process in
  `pixi run dev`) runs Vite/npm through the pixi-provided Node runtime, so the HMR
  server on `:5173` and its `/api → :8000` proxy behave identically on macOS and
  Windows — no separate Node/nvm install.
- **Portable broker/beat paths.** The filesystem Celery broker and the Beat
  schedule live under a git-ignored `backend/.celery/` tree (broker messages under
  `backend/.celery/broker/`, the Beat schedule at
  `backend/.celery/celerybeat-schedule`). These paths are built with `pathlib`, so
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
| **Database** | SQLite (`backend/db.sqlite3`) | Enterprise-managed **PostgreSQL** |
| **Object storage** | `FileSystemStorage` (`backend/media/`) | Enterprise **S3**-compatible object storage |
| **Celery broker** | Kombu `filesystem://` (`backend/.celery/broker/`) | Enterprise **Redis** |
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

The API and the built SPA are served by the `web` container (gunicorn); MinIO's
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

Django settings are split under `backend/config/settings/`:

| Module | Used for |
|---|---|
| `base.py` | Shared configuration (apps, DRF, Celery, storage, API-docs toggle); its SQLite + filesystem-storage defaults **are** the containerless defaults |
| `local.py` | Containerless local dev — the default `DJANGO_SETTINGS_MODULE` for `manage.py`, Celery, and pytest; swaps in the filesystem Celery broker + `django-db` results |
| `production.py` | Production hardening for the container/OCP path; the default for `wsgi.py`/`asgi.py` |

Configuration is environment-driven; never commit secrets or `.env` files.

## Everyday tasks

| Task | What it does |
|---|---|
| `pixi run dev` | Start the containerless stack (web + worker + beat + frontend HMR) |
| `pixi run fe-dev` | Start just the Vite HMR frontend on :5173 (proxies `/api` → :8000) |
| `pixi run migrate` | Apply database migrations |
| `pixi run test` | Backend unit tests (fast) |
| `pixi run test-integration` | Backend integration tests |
| `pixi run cov` | Full backend suite with the ≥90% coverage gate |
| `pixi run fmt` / `pixi run lint` / `pixi run check` | Ruff format, Ruff lint, mypy |
| `pixi run docs-serve` | Live-preview this documentation site |
| `pixi run ci` | The full local gate — see [Testing](testing.md) |

Run `pixi task list` to see every available task.
