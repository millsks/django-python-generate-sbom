# Story 1.2: Docker Compose Full Stack

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Build-Time Amendment (2026-07-03) — pixi umbrella Docker topology

AD-13 was amended to make pixi the whole-project umbrella (see memory pixi-umbrella-toolchain). This re-shapes the Docker topology; where the tasks/ACs below reference a separate `frontend-build` service, a `frontend-dist` volume, or `build.context: ./backend` and `./frontend`, THIS WINS:

- **Single root `Dockerfile`** (build context `.`) installs the pixi env (Python + Node), builds the SPA into the image via `pixi run fe-build`, and runs `collectstatic`. The SPA is baked into the image — no separate frontend-build service, no shared `frontend-dist` volume.
- **7 services** (not 8): `web`, `worker-pipeline`, `worker-analysis`, `beat`, `postgres`, `redis`, `minio`. Each Django/Celery service runs from the one image via `pixi run <task>` (`web`, `worker-pipeline`, `worker-analysis`, `beat`).
- AC #4 (`build.context` per service) and AC #5 (`frontend-dist` volume) are superseded by the single-image approach. AC #1's service count becomes 7. AC #2 (`/health/`), #3 (healthcheck), #6 (no hardcoded secrets), #7 (`.env.example`) are unchanged.

## Story

As a developer,
I want to start the full application stack with a single command,
so that I can develop and test against real infrastructure locally.

## Acceptance Criteria

1. Given a `.env` file populated from `.env.example`, when I run `docker compose up` from the project root, then all eight services start successfully: `web`, `worker-pipeline`, `worker-analysis`, `beat`, `postgres`, `redis`, `minio`, and `frontend-build`.
2. Given all services running, when I send `GET /health/` with no authentication headers, then the response is `200 OK` with body `{"status": "ok"}`.
3. Given the Docker Compose `web` service healthcheck directive, when Django is ready to serve requests, then Docker marks the `web` container healthy and dependent services start.
4. Given `docker-compose.yml`, when I inspect the `build.context` for each service, then all Django services (`web`, `worker-pipeline`, `worker-analysis`, `beat`) use `./backend` and the `frontend-build` service uses `./frontend` (AD-13).
5. Given `docker-compose.yml`, when I inspect the volumes section, then a `frontend-dist` named volume is declared; `frontend-build` mounts it at `/app/dist` (write); `web` mounts it read-only at `/app/frontend/dist`.
6. Given `docker-compose.yml`, when I search for hardcoded secrets (passwords, keys, tokens), then none are found; all sensitive values reference environment variables.
7. Given `.env.example` committed to the repository, when a developer copies it to `.env` and fills in the required values, then `docker compose up` completes without error and all services become healthy.

## Tasks / Subtasks

- [ ] Task 1 — Backend Dockerfile (AC: #1, #4)
  - [ ] `backend/Dockerfile` builds the pixi environment and installs the project; entrypoint runs `collectstatic` then the given command
  - [ ] Base image supports pixi; use `pixi install --locked` in the build for reproducibility
  - [ ] Ensure `curl` is available in the image for the healthcheck
- [ ] Task 2 — Frontend build Dockerfile (AC: #1, #4, #5)
  - [ ] `frontend/Dockerfile` (or inline `build.context: ./frontend`) installs node, runs `npm ci && npm run build`, emits to `/app/dist`
  - [ ] The `frontend-build` service is a one-shot builder that populates the shared volume and exits
- [ ] Task 3 — Author `docker-compose.yml` at the project root (AC: #1, #3, #4, #5, #6)
  - [ ] Define all eight services exactly as in Dev Notes → Compose spec
  - [ ] `web`: `build.context: ./backend`, `gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 4`, healthcheck curling `/health/`, `depends_on: [postgres, redis, minio, frontend-build]`
  - [ ] `worker-pipeline`: `celery -A config.celery_app worker -Q pipeline -c 4`
  - [ ] `worker-analysis`: `celery -A config.celery_app worker -Q analysis -c 4`
  - [ ] `beat`: `celery -A config.celery_app beat -s /tmp/celerybeat-schedule`
  - [ ] `postgres: postgres:18`, `redis: redis:8`, `minio: minio/minio` with console
  - [ ] Declare the `frontend-dist` named volume; wire write mount on `frontend-build`, `:ro` mount on `web` at `/app/frontend/dist`
  - [ ] All env values via `${VAR}` / `env_file: .env` — zero literal secrets
- [ ] Task 4 — `GET /health/` endpoint (AC: #2)
  - [ ] Add an unauthenticated view returning `{"status": "ok"}` with `200`
  - [ ] Wire it in `backend/config/urls.py` as `/health/` (must NOT require auth, must NOT hit the DB so it stays green during boot ordering)
  - [ ] Unit test asserts 200 + exact body + no auth required
- [ ] Task 5 — `.env.example` (AC: #6, #7)
  - [ ] List every variable from Dev Notes → Environment variables with safe non-secret placeholders
  - [ ] Confirm `.env` is gitignored (already present in repo `.gitignore`)
- [ ] Task 6 — MinIO bucket bootstrap (AC: #1, #7)
  - [ ] Ensure the target bucket exists on first run (init container, `mc` sidecar command, or documented one-liner) so `django-storages` writes succeed
- [ ] Task 7 — End-to-end verification (AC: #1, #2, #3, #7)
  - [ ] `docker compose up` from a clean `.env`; confirm all eight services reach healthy/running
  - [ ] `curl -f http://localhost:8000/health/` returns `{"status": "ok"}`
  - [ ] `pixi run ci` from `backend/` still exits 0 (health view + its test included)

## Dev Notes

### Compose spec (solution-design.md § 9 — authoritative)

```yaml
services:
  frontend-build:
    build:
      context: ./frontend
    command: sh -c "npm ci && npm run build"
    volumes:
      - frontend-dist:/app/dist

  web:
    build:
      context: ./backend
    command: gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 4
    volumes:
      - frontend-dist:/app/frontend/dist:ro   # makes frontend/dist available to collectstatic
    depends_on: [postgres, redis, minio, frontend-build]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s

  worker-pipeline:
    build:
      context: ./backend
    command: celery -A config.celery_app worker -Q pipeline -c 4
    depends_on: [postgres, redis, minio]

  worker-analysis:
    build:
      context: ./backend
    command: celery -A config.celery_app worker -Q analysis -c 4
    depends_on: [postgres, redis, minio]

  beat:
    build:
      context: ./backend
    command: celery -A config.celery_app beat -s /tmp/celerybeat-schedule
    depends_on: [postgres, redis]

  postgres:
    image: postgres:18
    environment:
      POSTGRES_DB: sbom
      POSTGRES_USER: sbom
      POSTGRES_PASSWORD: sbom

  redis:
    image: redis:8

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: miniominio

volumes:
  frontend-dist:
```

Note on AC #6 vs. the spec: the illustrative postgres/minio literals above are dev defaults. To satisfy AC #6 (no hardcoded secrets), move them into `.env` and reference via `${POSTGRES_PASSWORD}` etc., with `env_file: .env` on the relevant services. Keep the compose shape identical.

### Health endpoint contract (ARCHITECTURE-SPINE.md § Consistency Conventions)

`GET /health/` → `{"status": "ok"}` with `200`, unauthenticated. Used by the Docker Compose `healthcheck:` directive. Keep it DB-free so the container reports healthy independent of migration/DB-boot timing; it exists purely to gate `depends_on` ordering.

### The frontend-dist volume flow (AD-5, AD-13)

`frontend-build` runs `npm run build` → writes `frontend/dist/` into the `frontend-dist` volume at `/app/dist`. `web` mounts that volume read-only at `/app/frontend/dist`, so when Django's entrypoint runs `collectstatic`, `STATICFILES_DIRS` (`BASE_DIR.parent.parent / 'frontend' / 'dist'`) resolves to populated assets. WhiteNoise then serves them. Story 1.4 wires the Django side; this story only guarantees the volume plumbing exists.

### Environment variables (solution-design.md § 8)

| Variable | Example (.env.example) | Notes |
|---|---|---|
| `SECRET_KEY` | `changeme-generate-a-real-one` | required |
| `DEBUG` | `True` | local dev |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | |
| `DATABASE_URL` | `postgres://sbom:sbom@postgres:5432/sbom` | |
| `REDIS_URL` | `redis://redis:6379/0` | broker + cache |
| `AWS_STORAGE_BUCKET_NAME` | `sbom-artifacts` | |
| `AWS_S3_ENDPOINT_URL` | `http://minio:9000` | MinIO local |
| `AWS_ACCESS_KEY_ID` | `minio` | |
| `AWS_SECRET_ACCESS_KEY` | `miniominio` | |
| `SBOM_MAX_CONCURRENT_JOBS_PER_ORG` | `5` | |
| `SBOM_LTS_REGISTRY` | (empty → built-in) | |
| `CELERY_TASK_SOFT_TIME_LIMIT` | `1800` | |
| `CELERY_TASK_TIME_LIMIT` | `2100` | |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `sbom` | compose service env |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `minio` / `miniominio` | compose service env |

### Dependency & sequencing notes

- This story depends on Story 1.1 (the `backend/` scaffold, `config/urls.py`, pixi env) existing.
- The Celery worker/beat services reference `config.celery_app`, which is fully wired in Story 1.3. To keep this story independently bootable, `config/celery_app.py` must at least import-resolve. If Story 1.3 is not yet done when this runs, add a minimal importable `config/celery_app.py` here; Story 1.3 fills in the Beat schedule and settings binding. Prefer running 1.3 before/with 1.2 if possible, but do not block on it.
- The `web` entrypoint depends on Django settings + DB config from Story 1.3. A minimal `local` settings module must exist for `gunicorn config.wsgi` to boot.

### Constraints / guardrails

- NFR-5.1: a single `docker compose up` from a clean clone + configured `.env` starts the full stack.
- NFR-5.2: all config via env vars; no committed secrets (AC #6).
- Never commit the real `.env`; only `.env.example`.
- `postgres:18`, `redis:8`, `minio/minio` images per the spec — do not substitute versions.

### Project Structure Notes

- `docker-compose.yml`, `README.md`, `LICENSE` live at the **project root** (AD-13); Dockerfiles live inside their build contexts (`backend/Dockerfile`, `frontend/Dockerfile`).
- The health view is the first code added to `<project_slug>/` — place it in a small `core`/`common` module or directly on `config/urls.py` with an inline view; avoid inventing an app just for health.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2: Docker Compose Full Stack]
- [Source: solution-design.md#9. Docker Compose]
- [Source: solution-design.md#8. Configuration]
- [Source: ARCHITECTURE-SPINE.md#AD-13 — Monorepo layout]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Health check]
- [Source: ARCHITECTURE-SPINE.md#Structural Seed — System containers]
- [Source: prd.md#NFR-5.1, NFR-5.2]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
