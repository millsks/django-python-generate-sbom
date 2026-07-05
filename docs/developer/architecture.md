# Architecture

The authoritative design record is the **architecture spine** in
`_bmad-output/planning-artifacts/architecture/`. This page summarizes it for
day-to-day development; when the two disagree, the spine wins.

## Design paradigm

**Layered modular monolith with an async pipeline.** The system is a single
deployable Django application. Module boundaries are Django apps; cross-module calls
go through Python **service functions**, never HTTP. A Celery pipeline runs those same
service functions asynchronously, so there is no duplicate business logic between the
HTTP and async paths.

```
HTTP / React SPA   →   DRF Views   →   Service Layer   →   ORM / External APIs
                                ↑
                        Celery Tasks (same service layer, no HTTP)
```

The React SPA is the only UI. It talks to the backend exclusively through the
versioned REST API — there is no server-side rendering of business data.

## Containers

| Container | Role |
|---|---|
| `web` | Django + DRF (gunicorn) — serves the REST API and the built SPA assets |
| `worker-pipeline` | Celery worker on the `pipeline` queue (sequential SBOM phases) |
| `worker-analysis` | Celery worker on the `analysis` queue (parallel enrichment) |
| `beat` | Celery Beat — scheduled maintenance (artifact expiry, mapping refresh) |
| `postgres` | Relational store |
| `redis` | Celery broker + result backend |
| `minio` | S3-compatible artifact blob storage |

## Invariants (selected)

These are the load-bearing rules from the spine. Respect them when adding code.

- **AD-1 — Modular monolith, no inter-app HTTP.** Apps call each other through service
  functions, not network calls.
- **AD-2 — `OrgScopedModel` for org isolation.** Tenant-scoped models inherit from
  `OrgScopedModel` and are always filtered by the active org.
- **AD-3 — Service-layer purity.** Business logic lives in `services.py` modules that
  take plain arguments and are callable from both views and tasks.
- **AD-4 — Two Celery queues.** `pipeline` (sequential generation) and `analysis`
  (parallel enrichment) — see [the pipeline](pipeline.md).
- **AD-5 — React SPA, REST only.** No Django template coupling to business data.
- **AD-6 — Storage triad.** Artifact **blobs live in S3/MinIO only** — never in
  PostgreSQL or Redis. The pipeline passes storage **keys**, not blobs, between phases.
- **AD-7 — Per-org concurrency gate at enqueue.** The generate endpoint gates
  concurrent jobs per org and creates the `ManifestUpload` + `SBOMJob` in one
  transaction before dispatch.
- **AD-8 — API keys via an `AbstractAPIKey` subclass** (`OrgApiKey`).
- **AD-10 — `delay_on_commit()` for all task dispatch from views** — tasks fire only
  after the DB transaction commits.
- **AD-11 — Artifact downloads via presigned URL**, never proxied through Django.
- **AD-12 — `SBOMJob.status` is written exclusively by Celery task code**, never by a
  view.
- **AD-13 — Monorepo layout.** `backend/` and `frontend/` are project-root peers under
  a pixi umbrella (see [Project Layout](project-layout.md)).

## Dependency direction

The app dependency direction is one-way: `sbom → manifests`, and both depend on
`common`/`users`. The `sbom` app is the importer of the manifest upload service
(so the generate view lives in `sbom/views.py`). Keep new dependencies pointing the
same way to avoid import cycles.
