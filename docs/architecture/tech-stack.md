# Tech Stack

A survey of the significant frameworks and libraries behind **Python Inventory Supply
Lens**, grouped by layer. This is not an exhaustive dependency list — the floors shown
are those declared in `pixi.toml`, and exact resolved versions live in `pixi.lock`.

For how these pieces fit together, see [Architecture](architecture.md); for getting them
running locally, see [Local Development](../developer/setup.md).

---

## At a glance

| Layer | Choice |
| --- | --- |
| Web framework | Django (server-rendered UI + DRF API in one project) |
| Async work | Celery, two queues, Redis or filesystem broker |
| Front end | Bootstrap 5 + htmx, vendored — no SPA, no build step, no CDN |
| Data | PostgreSQL in containers, SQLite for local dev |
| Blob storage | S3-compatible (MinIO locally) via django-storages |
| Packaging / tasks | Pixi (conda-forge) as the single environment and task runner |
| Distribution | Docker Compose stack, or a containerless local run on macOS / Linux / Windows |

---

## Core web stack

| Library | Floor | Role |
| --- | --- | --- |
| **Django** | ≥5.1 | The application framework. `src/` layout with `config` (settings/celery/wsgi), `django_service` (host project: concrete `User`, templates, static), and `inventory` (the one reusable app). Settings split into `base` / `local` / `test`. |
| **Django REST Framework** | ≥3.15 | The JSON API layer. Dual auth: API key for programmatic callers, session auth for the web UI. |
| **djangorestframework-api-key** | ≥3.1 | Org-scoped API keys, wrapped by a custom `OrgApiKeyAuthentication` class. |
| **drf-spectacular** + **-sidecar** | ≥0.27 | OpenAPI 3 schema generation; the sidecar ships Swagger/Redoc assets locally instead of from a CDN. |
| **django-environ** | ≥0.11 | 12-factor configuration — `DATABASE_URL` and friends read from the environment. |
| **WhiteNoise** | ≥6.6 | Static file serving from the app process. |
| **gunicorn** | ≥22 | Production WSGI server. Unix-only, so it is scoped to the non-Windows platforms; Windows local dev uses `runserver`. |

## Asynchronous processing

The SBOM pipeline is a Celery chain across two queues, `pipeline` and `analysis`.

| Library | Floor | Role |
| --- | --- | --- |
| **Celery** | ≥5.3 | Task queue driving generation and analysis. Prefork pool on Unix; `--pool=solo` on Windows. |
| **django-celery-results** | ≥2.5 | Database result backend, so containerless local dev needs no Redis. The container path keeps the Redis backend. |
| **redis-py** | ≥5 | Broker and result backend on the container/production path. |
| **Flower** | ≥2 | Celery monitoring UI at `localhost:5555`. |
| **honcho** | ≥2 | Pure-Python Procfile runner. `pixi run dev` starts web + worker + beat together, identically on macOS and Windows. |
| **pywin32** | ≥306 | Windows only, and required: Kombu's `filesystem://` transport imports it unconditionally under `nt`, so the local worker will not start without it. |

## Server-rendered UI

There is no SPA. The React front end was retired, which removed the Node runtime, the
second port, and the build step — the UI is Django templates, and every asset is vendored
rather than pulled from a CDN.

| Library | Floor | Role |
| --- | --- | --- |
| **Bootstrap 5** | vendored | Layout, components, and the light/dark theme. |
| **htmx** | vendored | Partial-page interactivity without a JavaScript framework. |
| **django-crispy-forms** + **crispy-bootstrap5** | ≥2.6 / ≥2026.3 | Bootstrap-styled form rendering. |
| **django-tables2** | ≥3.0 | Sortable, paginated server-rendered tables. |
| **django-filter** | ≥26.1 | Filter backends shared by the tables and the DRF API. |

## SBOM domain

| Library | Floor | Role |
| --- | --- | --- |
| **cyclonedx-python-lib** | ≥11.11 | CycloneDX document construction — the primary SBOM output format. |
| **lib4sbom** | ≥0.10.4 | SBOM parsing and multi-format handling, including SPDX. |
| **uv** | ≥0.11.26 | Invoked as an external tool to resolve uploaded Python dependency manifests. |
| **openpyxl** | ≥3.1.5 | Spreadsheet export of analysis reports. |

## Data, storage, and outbound HTTP

| Library | Floor | Role |
| --- | --- | --- |
| **psycopg** | ≥3.1 | PostgreSQL driver for the container and production paths. |
| **PostgreSQL 18** | image | Container database. Local dev runs on SQLite, tuned for the three-process write contention `pixi run dev` creates. |
| **django-storages** + **boto3** | ≥1.14 / ≥1.34 | S3-compatible artifact and manifest blob storage. **MinIO** provides the local S3 endpoint. |
| **requests** | ≥2.32 | Outbound HTTP to vulnerability and package-metadata sources. |
| **requests-cache** | ≥1.2 | Response caching to avoid re-querying upstream services. |
| **requests-ratelimiter** | ≥0.7 | Client-side rate limiting for those same services. |
| **tenacity** | ≥9 | Retry policy around transient upstream failures. |
| **structlog** | ≥24 | Structured logging throughout — the stdlib `logging` module is not used. |

## Development toolchain

| Tool | Floor | Role |
| --- | --- | --- |
| **Pixi** | — | The single package manager and task runner for the whole project, conda-forge first. Every command runs through `pixi run`. |
| **pytest** + **pytest-django** + **pytest-cov** | ≥8 / ≥4.9 / ≥6 | Unit and integration suites behind a 90% coverage gate. |
| **mypy** (strict) | ≥1.13 | Static typing, with **django-stubs** and **djangorestframework-stubs** and the Django plugin. |
| **ruff** | ≥0.14 | Linting and formatting, 120-column, Google-convention docstrings. |
| **bandit** | ≥1.7 | Static security scanning of `src/`. |
| **hatchling** | ≥1.25 | Wheel build backend. Its `sources` mapping is what makes the app importable as `inventory` rather than `django_apps.inventory`. |
| **pre-commit** | ≥4 | Ruff, mypy, and Conventional Commit validation on every commit. |
| **git-cliff** | ≥2 | Changelog generation from Conventional Commits. |
| **MkDocs Material** + **mkdocstrings-python** | ≥9.5 / ≥1.11 | Documentation site, published to GitHub Pages. |

`pixi run ci` is the gate: pre-commit → wheel build → mypy → ruff lint → format check →
bandit → full coverage → strict docs build.

## Infrastructure and CI

**Docker Compose** brings up the full stack: `web`, `worker-pipeline`, `worker-analysis`,
`beat`, PostgreSQL 18, Redis 8, MinIO, and a one-shot bucket-creation job. All Django and
Celery services share a single umbrella image.

**GitHub Actions** runs the pipeline across six workflows (CI, docs, release, labeler,
maintenance, stale), using:

- `prefix-dev/setup-pixi` — environment provisioning, matching local exactly
- `codecov/codecov-action` — coverage reporting
- `SonarSource/sonarqube-scan-action` — SonarCloud quality gate
- `docker/build-push-action` + `setup-buildx-action` — image builds
- `actions/deploy-pages` + `upload-pages-artifact` — docs publishing
- `softprops/action-gh-release` — releases

---

## Notable architectural choices

- **One environment, one runner.** Pixi manages the entire project. There is no `pip`,
  `uv run`, or bare `python` path — a second environment would silently drift from
  `pixi.lock`.
- **Containerless local development is a first-class path.** `pixi run dev` runs the whole
  stack with no Docker: SQLite instead of PostgreSQL, a Kombu filesystem broker instead of
  Redis, a database result backend, and local disk instead of MinIO. It is supported on
  Windows as well as macOS and Linux.
- **One reusable Django app.** `inventory` holds the domain and stays free of the concrete
  `User` model; `django_service` is the host project that supplies it. The app can be
  lifted into another project.
- **No CDN, no SPA.** Every front-end asset is vendored into the repository, so the
  application runs in an air-gapped environment.
