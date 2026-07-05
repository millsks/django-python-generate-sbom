# Local Development

## Prerequisites

- [**pixi**](https://pixi.sh) — the single toolchain manager for the whole project
  (Python **and** Node). You do not need a separate `pip`, `conda`, `nvm`, or `npm`
  install step; pixi manages all of them.
- **Docker** + Docker Compose — to run the supporting services (PostgreSQL, Redis,
  MinIO) and, optionally, the whole stack.

## First-time setup

```sh
pixi install          # resolve and install the full environment (Python + Node)
pixi run bootstrap    # install the pre-commit + commit-msg git hooks
```

## Running the stack with Docker Compose

The fastest way to a working system is Compose, which starts every container
described in [Architecture](architecture.md):

```sh
pixi run docker-up      # build (if needed) and start all services in the background
pixi run docker-logs    # follow the logs
pixi run docker-down    # stop everything
```

The API and the built SPA are served by the `web` container; MinIO's console and the
Postgres/Redis ports are exposed for local inspection (see `docker-compose.yml`).

## Running pieces individually

For backend work you often want the services in Docker but the app processes in your
shell so you get fast reloads. Start the infra (`postgres`, `redis`, `minio`) with
Compose, then:

```sh
pixi run migrate            # apply database migrations
pixi run web                # gunicorn API server on :8000
pixi run worker-pipeline    # Celery worker: pipeline queue (sequential phases)
pixi run worker-analysis    # Celery worker: analysis queue (parallel enrichment)
pixi run beat               # Celery Beat scheduler (maintenance jobs)
pixi run flower             # Celery monitoring UI on :5555
```

The frontend dev server and build run through their own pixi tasks (`fe-*`); see the
task list below.

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

`UserManager.create_superuser` calls `grant_global_admin`, so the new superuser is
written into the ADMIN org and back-filled as an admin of every org. If you created
superusers before running the seed migration (or need an idempotent catch-up), run:

```sh
python manage.py bootstrap_admin_org    # ensure the ADMIN org exists; seed all superusers
```

Under Docker Compose, run these inside the `web` container (`pixi run docker-shell`,
then the same `python manage.py …` commands).

## Settings

Django settings are split under `backend/config/settings/`:

| Module | Used for |
|---|---|
| `base.py` | Shared configuration (apps, DRF, Celery, storage, API-docs toggle) |
| `local.py` | Local development overrides |
| `production.py` | Production hardening (e.g. API docs default **off**) |

Configuration is environment-driven; never commit secrets or `.env` files.

## Everyday tasks

| Task | What it does |
|---|---|
| `pixi run test` | Backend unit tests (fast) |
| `pixi run test-integration` | Backend integration tests |
| `pixi run cov` | Full backend suite with the ≥90% coverage gate |
| `pixi run fmt` / `pixi run lint` / `pixi run check` | Ruff format, Ruff lint, mypy |
| `pixi run docs-serve` | Live-preview this documentation site |
| `pixi run ci` | The full local gate — see [Testing](testing.md) |

Run `pixi task list` to see every available task.
