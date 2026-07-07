# django-python-generate-sbom

A self-hosted, open-source Django web service that accepts Python dependency
manifests and generates production-grade Software Bills of Materials (SBOMs) in
standard formats (CycloneDX, SPDX), alongside three analysis reports:
vulnerability findings, license obligations, and version currency — through
both a web UI and a REST API.

<!-- Status -->
[![CI](https://github.com/millsks/django-python-generate-sbom/actions/workflows/ci.yml/badge.svg)](https://github.com/millsks/django-python-generate-sbom/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/millsks/django-python-generate-sbom/branch/main/graph/badge.svg)](https://codecov.io/gh/millsks/django-python-generate-sbom)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=millsks_django-python-generate-sbom&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=millsks_django-python-generate-sbom)
[![Release](https://img.shields.io/github/v/release/millsks/django-python-generate-sbom)](https://github.com/millsks/django-python-generate-sbom/releases)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

<!-- Tooling -->
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-526cfe)](https://millsks.github.io/django-python-generate-sbom/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Typed: mypy](https://img.shields.io/badge/typed-mypy-blue)](https://mypy-lang.org/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)

> **Note:** this app is not published to any package index — it ships as
> self-hostable source with tagged GitHub Releases, so there are no PyPI or
> conda-forge version badges.

## Overview

Point the service at a Python dependency manifest and it resolves the full
dependency tree, produces a signed-off SBOM, and enriches it with four analyses
you can browse in the UI, export to Excel, or pull over the REST API. Everything
is multi-tenant and scoped to your organization.

**Features:**

- **Multi-format SBOMs** — CycloneDX and SPDX from `requirements.txt` (and
  prefixed variants), `pyproject.toml`, `pixi.toml` / `pixi.lock`, and conda
  `environment.yml`, with transitive dependencies resolved.
- **Vulnerability report** — known advisories (CVE/GHSA) with severity and CVSS.
- **License compliance** — per-package licenses grouped by legal-risk tier.
- **Version currency** — installed vs. latest, LTS tracking, and the
  conda-forge latest (via prefix.dev) flagged when it diverges from PyPI.
- **In-app SBOM viewer** and **Excel export** of every report.
- **Accounts & orgs** — registration, org switching, membership management,
  and API keys; session and API-key authentication.
- **Async pipeline** — a Celery workflow with live progress, MinIO artifact
  storage, and scheduled retention/cleanup.
- **Web UI** (React 19 + MUI) and a **REST API**, served from one origin.

## Documentation

Full documentation is published with MkDocs Material at
**<https://millsks.github.io/django-python-generate-sbom/>**:

- **[User Guide](https://millsks.github.io/django-python-generate-sbom/user-guide/)**
  — accounts, uploading manifests, and reading every report.
- **[How-To Guides](https://millsks.github.io/django-python-generate-sbom/how-to/)**
  — task-focused recipes.
- **[Developer Docs](https://millsks.github.io/django-python-generate-sbom/developer/)**
  — architecture, local setup, the SBOM pipeline, and testing.
- **[API Reference](https://millsks.github.io/django-python-generate-sbom/api/)**
  — the REST endpoints.

Contributions are welcome — see **[CONTRIBUTING.md](CONTRIBUTING.md)**.

## Screenshots

<!-- TODO: capture web-UI screenshots for the README/docs (documentation follow-up). -->

_Screenshots of the web UI are a pending documentation addition._

## Architecture

A modular Django monolith (`backend/`) with a Celery async pipeline, fronted by a
React SPA (`frontend/`). **Pixi is the umbrella toolchain for the whole project**:
a single root `pixi.toml` installs both the Python environment and the Node
runtime, and orchestrates every task.

```
django-python-generate-sbom/   ← project root (pixi umbrella)
  pixi.toml                     # Python env + Node runtime + all tasks
  backend/                      # Django + Celery
  frontend/                     # React + Vite SPA
  Dockerfile                    # umbrella image (Python + Node); SPA baked in
  docker-compose.yml            # full local stack (web, workers, postgres, redis, minio)
```

## Quick start

Requires [pixi](https://pixi.sh). Node.js and Python are installed by pixi — no
separate toolchain setup needed.

```sh
pixi install          # installs Python + Node environments
pixi run bootstrap    # installs the pre-commit git hooks
pixi run ci           # full validation gate (build · type-check · lint · coverage · docs)
```

The Docker stack is the simplest way to run the whole app — the SPA is built into
the image and served by Django, so there is no separate frontend server to start:

```sh
cp .env.example .env          # then edit SECRET_KEY (and any passwords) in .env
docker compose up --build     # web, both Celery workers, beat, postgres, redis, minio
```

Wait until the `web` service is healthy, then open:

| URL | What it is |
|---|---|
| <http://localhost:8000> | The web UI (React SPA) |
| <http://localhost:8000/admin/> | Django admin site |
| <http://localhost:8000/health/> | Health check (JSON) |
| <http://localhost:9001> | MinIO console (login with `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` from `.env`) |

Then **register** at `/register` — new accounts start **without** an organization,
so you'll be sent to **sign in** at `/login`. A new user is **restricted to the
home page** until an admin adds them to an organization (creating an organization
is reserved for **global admins**). The seeded superuser is a global admin and can
create the first organization and add members from there. Once you have an active
org, **upload** a manifest at `/upload`; all SBOM data is scoped to your active
organization. See the
[User Guide](https://millsks.github.io/django-python-generate-sbom/user-guide/)
for the full walkthrough.

The app has three role tiers: **members** (work within their orgs),
**organization admins** (manage an org's membership and API keys), and **global
admins** (platform admins who belong to a system **Admin** org, are an admin of
every organization, and can create orgs and manage the global-admin tier).

To reach the Django admin at `/admin/`, create a superuser in the running `web`
container:

```sh
docker compose exec web pixi run python backend/manage.py createsuperuser
```

The first superuser is seeded into the system **ADMIN** organization, making them
a _global admin_ with oversight of every organization. See the
[Developer Docs](https://millsks.github.io/django-python-generate-sbom/developer/)
for the org-membership and global-admin model.

Alternatively, set `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` in `.env` and the
`web` container **auto-seeds** that superuser (as a global admin) on startup — no manual step
(dev convenience; never commit real credentials).

## Development

All tasks run from the project root via `pixi run <task>`:

| Task | Purpose |
|---|---|
| `fmt` · `lint` · `check` | Format, lint, and type-check the backend (ruff, mypy) |
| `test` · `test-integration` | Backend unit / integration tests |
| `cov` | Full test suite with the 90% coverage gate |
| `fe-lint` · `fe-typecheck` · `fe-test` · `fe-build` | Frontend lint / types / tests / build |
| `docs-serve` · `docs-build` | Preview / build the documentation site |
| `build` | Build the backend package distribution |
| `ci` | Full validation sequence (the merge gate) |

`pixi run ci` must exit 0 before any change is considered done. See the
[Developer Docs](https://millsks.github.io/django-python-generate-sbom/developer/)
and [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow.

## License

Licensed under the [Apache License 2.0](LICENSE).
