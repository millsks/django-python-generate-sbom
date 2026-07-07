# Reference

Deployment reference material: the full environment-variable inventory, probe and
autoscaling settings, resource sizing, TLS, and observability. Pair this with the
[Migration Guide](migration-guide.md).

## Environment variables

Every value below is read from the environment by Django
(`backend/config/settings/base.py` and `backend/config/settings/production.py`).
The **Where** column is the recommendation for OpenShift: put non-sensitive values
in a **ConfigMap**, sensitive values in a **Secret** (or an
[ESO/Vault-backed](migration-guide.md#configuration-and-secrets) source).

### Django core

| Variable | Purpose | Where | Example |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Selects the settings module. Must be `config.settings.production`. | ConfigMap | `config.settings.production` |
| `SECRET_KEY` | Django cryptographic signing key. | **Secret** | `<50+ random chars>` |
| `DEBUG` | Debug mode; must be `False` in production. | ConfigMap | `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts Django will serve. Must include the Route host. | ConfigMap | `sbom.apps.example.com` |
| `API_DOCS_ENABLED` | Serves `/api/schema/`, `/api/docs/`, `/api/redoc/`. Defaults to `True`; set `false` to hide them in production. | ConfigMap | `false` |

### Database

| Variable | Purpose | Where | Example |
|---|---|---|---|
| `DATABASE_URL` | Full Postgres DSN (host, port, db, user, password). Read via `env.db()`. | **Secret** (contains password) | `postgres://user:pass@pg.example.com:5432/sbom` |

### Redis / Celery

| Variable | Purpose | Where | Example |
|---|---|---|---|
| `REDIS_URL` | Celery broker **and** result backend **and** the shared external-API cache. | **Secret** if it carries auth, else ConfigMap | `redis://:pass@redis.example.com:6379/0` |
| `REQUESTS_CACHE_BACKEND` | External-API HTTP cache backend. Use `redis` in production so the cache is shared across analysis workers. | ConfigMap | `redis` |
| `CELERY_TASK_SOFT_TIME_LIMIT` | Soft per-task timeout (seconds). | ConfigMap | `1800` |
| `CELERY_TASK_TIME_LIMIT` | Hard per-task timeout (seconds). | ConfigMap | `2100` |

### Object storage (django-storages / boto3)

| Variable | Purpose | Where | Example |
|---|---|---|---|
| `AWS_STORAGE_BUCKET_NAME` | Artifact bucket name. | ConfigMap | `sbom-artifacts` |
| `AWS_S3_ENDPOINT_URL` | **Server-side** (in-cluster) S3 endpoint the app uses to read/write blobs. | ConfigMap | `https://s3.internal.example.com` |
| `AWS_S3_PUBLIC_ENDPOINT_URL` | **Browser-reachable** endpoint baked into presigned download URLs (AD-11). See [below](#presigned-url-public-endpoint-ad-11). | ConfigMap | `https://s3.example.com` |
| `AWS_ACCESS_KEY_ID` | Object-storage access key. | **Secret** | `<access-key>` |
| `AWS_SECRET_ACCESS_KEY` | Object-storage secret key. | **Secret** | `<secret-key>` |

### Pipeline and analysis tuning

| Variable | Purpose | Where | Example |
|---|---|---|---|
| `SBOM_MAX_CONCURRENT_JOBS_PER_ORG` | Per-org concurrency gate at enqueue (AD-7). | ConfigMap | `5` |
| `ARTIFACT_RETENTION_DAYS` | Days before artifact blobs are purged by the Beat cleanup. Metadata is kept forever. | ConfigMap | `30` |
| `SBOM_LTS_REGISTRY` | JSON file path or inline JSON of package→LTS-version overrides. | ConfigMap | `{}` |
| `PARSELMOUTH_MAPPING_URL` | conda↔PyPI bulk name-mapping source (refreshed by a Beat task). | ConfigMap | *(default upstream URL)* |
| `PARSELMOUTH_PYPI_TO_CONDA_URL` | Per-package PyPI→conda disambiguation lookup; set empty to disable the network call. | ConfigMap | *(default upstream URL)* |
| `LOG_JSON` | JSON structured logs when `True` (the production default). | ConfigMap | `True` |

### Initial superuser seeding

Consumed by the `seed-superuser` step in the [migrate Job](migration-guide.md#migrations-and-seeding-as-a-job), not by the web/worker Pods.

| Variable | Purpose | Where | Example |
|---|---|---|---|
| `DJANGO_SUPERUSER_EMAIL` | Email of the auto-seeded global admin. Idempotent — a no-op if the user exists. | ConfigMap or Secret | `admin@example.com` |
| `DJANGO_SUPERUSER_PASSWORD` | Password for the seeded superuser. | **Secret** | `<initial-admin-password>` |

### Compose-only variables (do **not** carry into OCP)

These configure the local Compose backing containers and have **no** role in
OpenShift, where those services are external:

| Variable | Why it is dropped |
|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Configure the local `postgres` container only. The app reads `DATABASE_URL`; the enterprise DBA owns these. |
| `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | Configure the local `minio` container only. The app authenticates with `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`. |

## Health probes

The app exposes an unauthenticated `GET /health/` endpoint
(`backend/generate_sbom/common/views.py`) that returns `{"status": "ok"}` and
deliberately **does not touch the database**. That makes it safe for both probe
types on the `web` Deployment:

| Probe | Path | Guidance |
|---|---|---|
| **readiness** | `GET /health/` | Gates traffic; keep `initialDelaySeconds` small (~5s) and `periodSeconds` ~10s. |
| **liveness** | `GET /health/` | Restarts a wedged Pod; use a slightly longer `initialDelaySeconds` (~15s) so a slow start is not killed. |

Workers and Beat have no HTTP server. A simple process-liveness check (the container
exits if the Celery process dies, and the Deployment restarts it) is sufficient; add
a Celery `inspect ping` exec probe only if you need finer detection.

## Resource requests and limits

Set requests so the scheduler places Pods sensibly and limits so a runaway task
cannot starve a node. Starting points to tune against real load:

| Component | requests (cpu/mem) | limits (cpu/mem) | Notes |
|---|---|---|---|
| `web` | 250m / 512Mi | 1 / 1Gi | gunicorn runs 4 workers; scale replicas via HPA. |
| `worker-pipeline` | 250m / 512Mi | 1 / 1Gi | Sequential SBOM generation; CPU-bound during parsing. |
| `worker-analysis` | 500m / 512Mi | 1 / 1Gi | Parallel enrichment with external API calls; benefits from more replicas. |
| `beat` | 50m / 128Mi | 250m / 256Mi | Lightweight scheduler; **1 replica**. |
| migrate Job | 250m / 512Mi | 1 / 1Gi | Short-lived. |

## Autoscaling (HPA)

The stateless tiers autoscale well. Attach an
[HPA](migration-guide.md#hpa-and-networkpolicy-illustrative) to `web`,
`worker-pipeline`, and `worker-analysis`; leave `beat` at a fixed single replica.
CPU utilization (~70%) is a reasonable first metric; the analysis workers may also
benefit from a queue-depth custom metric if your cluster exposes one.

## Route and TLS

The `web` Service is exposed via an OpenShift **Route** with **edge TLS termination**
and an HTTP→HTTPS redirect. TLS is mandatory, not optional, because
`production.py` sets:

- `SESSION_COOKIE_SECURE = True` and `CSRF_COOKIE_SECURE = True` — cookies are only
  sent over HTTPS, so plain HTTP breaks login and any state-changing request.
- `SECURE_HSTS_SECONDS = 31536000` with subdomain include + preload — browsers will
  refuse plain HTTP after the first visit.

Add the Route host to `ALLOWED_HOSTS`. If the platform terminates TLS at a
load balancer ahead of the Route, ensure the forwarded-proto header is honored so
Django knows the request is secure.

## Observability

- **Logs.** Production emits **JSON structured logs** to stdout
  (`configure_structlog(json_logs=True)` in `production.py`, `LOG_JSON=True`).
  OpenShift's cluster logging stack (or any stdout collector) ingests them directly —
  no sidecar or file scraping needed. Keep `LOG_JSON=True` so log aggregation stays
  machine-parseable.
- **Celery monitoring (optional).** The `flower` pixi task
  (`celery -A config.celery_app flower --port=5555`) provides a task-monitoring UI.
  If you want it in-cluster, add a small Deployment + Service + Route for it, but
  **protect it** — Flower exposes task detail and control, so put it behind
  authentication or restrict the Route. It is optional and not required for the app
  to run.
- **Metrics.** There is no built-in Prometheus endpoint; rely on platform-level Pod
  metrics (CPU/memory, used by the HPA) and Celery/Redis queue metrics from the
  enterprise Redis if available.

## Presigned-URL public endpoint (AD-11)

The most subtle networking requirement. Artifact downloads are **not** proxied
through Django — the app issues a **presigned URL** and the browser fetches the blob
**directly** from object storage (invariant AD-11). The URL is signed against
whatever host is configured, so:

- `AWS_S3_ENDPOINT_URL` is the **server-side** endpoint the app uses to *write* and
  *sign* blobs — typically an internal, cluster-reachable address.
- `AWS_S3_PUBLIC_ENDPOINT_URL` is the **browser-reachable** host that must appear in
  the presigned URL. The custom storage backend
  (`generate_sbom.common.storage.PublicEndpointS3Storage`) rewrites presigned URLs to
  use it.

If `AWS_S3_PUBLIC_ENDPOINT_URL` points at an internal-only host (the classic
mistake, mirroring the local `minio:9000` problem), downloads fail in the user's
browser even though everything works server-side. **Always test a real download**
during the smoke test, from a browser outside the cluster, before cutover.
