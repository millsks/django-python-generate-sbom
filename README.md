# django-python-generate-sbom

A self-hosted, open-source Django web service that accepts Python dependency
manifests and generates production-grade Software Bills of Materials (SBOMs) in
standard formats (CycloneDX, SPDX), alongside four analysis reports:
vulnerability findings, license obligations, dependency graph, and version
currency — through both a web UI and a REST API.

<!-- Badges: CI status, coverage, and PyPI version are added once the project publishes. -->

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

## Installation

Requires [pixi](https://pixi.sh). Node.js and Python are installed by pixi — no
separate toolchain setup needed.

```sh
pixi install          # installs Python + Node environments
pixi run bootstrap    # installs the pre-commit git hooks
```

## Quick start

```sh
pixi run test         # backend unit tests
pixi run ci           # full validation gate (build · type-check · lint · coverage)
```

Django management commands run inside the pixi environment:

```sh
pixi run python backend/manage.py migrate
```

## Using the web UI

The whole app (React SPA + REST API + admin) is served from a single origin. The
Docker stack is the simplest way to run it — the SPA is built into the image and
served by Django, so there is no separate frontend server to start.

### 1. Start the stack

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
| <http://localhost:9001> | MinIO console (object storage; login with `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` from `.env`) |

### 2. Register and sign in

1. Go to **<http://localhost:8000/register>** and submit your email and a password.
   This creates your account **and a personal organization** (named from your
   email prefix) in one step. Registration does not sign you in automatically.
2. Go to **<http://localhost:8000/login>** and sign in with the same credentials.
   Login establishes a session cookie; the SPA then routes you to the dashboard.

All SBOM data is scoped to your active organization, so every new account starts
with its own private workspace.

### 3. Generate an SBOM

Open **<http://localhost:8000/upload>** and complete the form:

- **Manifest file** — a Python dependency file (`requirements.txt`,
  `pyproject.toml`, `pixi.toml`, `pixi.lock`, or a conda `environment.yml`).
- **Application ID**, **Component Name**, **GitHub Repository URL**, and
  **Source Branch** — all four are **required**. They are embedded as provenance
  metadata at the top of the generated SBOM.
- **Output format** — CycloneDX JSON/XML or SPDX 2.3 JSON.

Submitting starts an async job. Track its progress on the dashboard; when it
completes, download the SBOM — the download is a redirect to a short-lived
presigned URL, so the file is served directly from object storage.

### UI routes and the API they call

| UI route | Purpose | Backing API |
|---|---|---|
| `/register` | Create account + personal org | `POST /api/v1/auth/register/` |
| `/login` · `/logout` | Session sign in / out | `POST /api/v1/auth/login/` · `/logout/` |
| `/dashboard` | Your jobs and their status | `GET /api/v1/sbom/status/{task_id}/` |
| `/upload` | Submit a manifest for SBOM generation | `POST /api/v1/sbom/generate/` |
| download | Fetch a finished SBOM | `GET /api/v1/sbom/result/{task_id}/` → 303 presigned URL |
| `/members` | Manage org members | `GET/POST /api/v1/orgs/members/` |
| `/keys` | Manage API keys for the REST API | `GET/POST /api/v1/keys/` |

Routes other than `/`, `/register`, and `/login` require an active session.

### Admin access (optional)

To reach the Django admin at `/admin/`, create a superuser inside the running
`web` container:

```sh
docker compose exec web pixi run python backend/manage.py createsuperuser
```

## Development

All tasks run from the project root via `pixi run <task>`:

| Task | Purpose |
|---|---|
| `fmt` | Format the backend (`ruff format`) |
| `lint` | Lint the backend (`ruff check`) |
| `check` | Type-check the backend (`mypy`, strict) |
| `test` | Backend unit tests |
| `test-integration` | Backend integration tests |
| `cov` | Full test suite with the 90% coverage gate |
| `build` | Build the backend package distribution |
| `ci` | Full validation sequence (the merge gate) |

`pixi run ci` must exit 0 before any change is considered done.

## License

Licensed under the [Apache License 2.0](LICENSE).
