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

## Accounts, orgs, and the global-admin tier

Identity and tenancy are deliberately **decoupled**. A `User` is a standalone
account; an `Org` is a tenant boundary; an `OrgMembership` links the two with a
role (`admin` or `member`). See the [Data Model](data-model.md) for the fields.

- **Zero-org identity.** A freshly registered user has **no** memberships —
  registration creates the account only, never a "personal" org. Authentication
  is therefore independent of org membership: the SPA establishes identity through
  `GET /auth/me/`, which succeeds for a user with no orgs. Anything org-scoped
  resolves the active org separately (`get_request_org`), and returns `None` when
  the user belongs to no org.

- **The system ADMIN org.** Exactly one org is distinguished by
  `Org.is_admin_org=True` (seeded by a data migration). Its members are **global
  admins** — a deliberate, documented cross-org superuser tier.

- **Global admins are real memberships everywhere.** Rather than special-casing
  authorization, a global admin is provisioned as a genuine
  `OrgMembership(role=ADMIN)` row in **every** non-admin org, existing and future.
  `create_org` auto-provisions all current global admins into any new org, and
  `grant_global_admin` back-fills a newly promoted admin into every existing org.
  Because the rows are real, the permission checks in `users/auth.py`
  (`get_request_org` / `get_admin_org`) treat a global admin as an ordinary admin
  of each org with **no** extra branching — the isolation model does not need to
  know the tier exists.

- **Superuser seeding.** `UserManager.create_superuser` calls
  `grant_global_admin`, so any Django superuser becomes a global admin as soon as
  the ADMIN org exists. The `bootstrap_admin_org` management command is the
  idempotent catch-up path: it ensures the ADMIN org row is present and back-fills
  every existing superuser (covering superusers created before the hook, or before
  migrations ran). See [Setup](setup.md).

- **Non-stranding guards.** Because global admins are real memberships,
  membership-removal services (`remove_member` / `leave_org`) guard the tier: the
  ADMIN org can never lose its last member, and a global admin cannot be removed
  from a single normal org (they belong to all of them).

## Dependency direction

The app dependency direction is one-way: `sbom → manifests`, and both depend on
`common`/`users`. The `sbom` app is the importer of the manifest upload service
(so the generate view lives in `sbom/views.py`). Keep new dependencies pointing the
same way to avoid import cycles.
