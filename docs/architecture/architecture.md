# Architecture

The authoritative design record is the **architecture spine** in
`_bmad-output/planning-artifacts/architecture/`. This page summarizes it for
day-to-day development; when the two disagree, the spine wins.

## Design paradigm

**Layered modular monolith with an async pipeline.** The system is a single
deployable Django application. Module boundaries are packages inside the single
`inventory` app; cross-module calls go through Python **service functions**, never HTTP.
A Celery pipeline runs those same service functions asynchronously, so there is no
duplicate business logic between the HTTP and async paths.

```
Browser      →   Page views  ┐
                             ├→   Service Layer   →   ORM / External APIs
API client   →   DRF Views   ┘          ↑
                        Celery Tasks (same service layer, no HTTP)
```

The UI is **server-rendered Django templates**. Page views and DRF views are peers on
the same service layer: a page view calls `services.py` / `selectors.py` directly and
**never** issues an HTTP request to `/api/v1/` — that would be an in-process network hop,
which AD-1 forbids. Where the HTML and JSON paths need the same behaviour, it is extracted
into a shared service function so the two cannot drift apart.

`/api/v1/` remains the contract for scripted and CI/CD clients; it is not a private
backend for the UI.

## Containers

| Container | Role |
|---|---|
| `web` | Django + DRF (gunicorn) — serves the server-rendered UI, the REST API, and static assets |
| `worker-pipeline` | Celery worker on the `pipeline` queue (sequential SBOM phases) |
| `worker-analysis` | Celery worker on the `analysis` queue (parallel enrichment) |
| `beat` | Celery Beat — scheduled maintenance (the conda↔PyPI mapping refresh; **artifact purging is manual**, see below) |
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
- **AD-15 — Server-rendered UI.** Page views call the service layer directly and never
  the HTTP API. (This supersedes **AD-5**, which mandated a React SPA; Epic 21 reversed it.)
- **AD-6 — Storage triad.** Artifact **blobs live in S3/MinIO only** — never in
  PostgreSQL or Redis. The pipeline passes storage **keys**, not blobs, between phases.
  Expiry is *tracked* on every job (`artifacts_expire_at`) but **nothing is purged on a
  schedule** (Story 22.6): run `pixi run python manage.py purge_expired_artifacts --dry-run`
  to review, then the same command without the flag to delete. Job records are never removed
  (FR-8.1).
- **AD-7 — Per-org concurrency gate at enqueue.** The generate endpoint gates
  concurrent jobs per org and creates the `ManifestUpload` + `SBOMJob` in one
  transaction before dispatch.
- **AD-8 — API keys via an `AbstractAPIKey` subclass** (`OrgApiKey`).
- **AD-10 — `delay_on_commit()` for all task dispatch from views** — tasks fire only
  after the DB transaction commits.
- **AD-11 — Artifact downloads via presigned URL**, never proxied through Django.
- **AD-12 — `SBOMJob.status` is written exclusively by Celery task code**, never by a
  view.
- **AD-13 — `src/` layout under a pixi umbrella** — `src/{config,django_service,django_apps}`
  with `tests/` at the root (see [Project Layout](project-layout.md)).
- **AD-16 — One reusable app.** All domain code is in `inventory`, imported unqualified.
- **AD-17 — No concrete `User` import.** App code uses `settings.AUTH_USER_MODEL` and
  `get_user_model()`; the concrete model is owned by the host project.
- **AD-18 — No container on the local path or the gate.** Nothing reachable from
  `pixi run dev` or `pixi run ci` may invoke Docker or Podman, because neither is
  permitted on Windows in the destination organization. Containers remain how
  production runs; the Compose stack stays behind the opt-in `docker-*` tasks.

## Accounts, orgs, and the global-admin tier

!!! warning "The app has no authentication of its own"

    Story 21.24 **deleted** the login, registration, and logout surface, the access-control
    mixins, and the DRF permission class. Every page and endpoint is open, and an anonymous
    caller acts as the organization named by `INVENTORY_DEFAULT_ORG_SLUG` (seeded by
    migration `0003`).

    Identity is the **host platform's** responsibility, supplied via OIDC and group claims
    when `inventory` is contributed to it (Epics 17-18). The enforcement that was removed
    was the wrong shape for that destination — Django session plus local `OrgMembership`
    roles — so it was deleted rather than flagged off.

    Do not re-add an app-owned session or role gate: that rebuilds exactly what was removed.
    `AD-14` in the architecture spine carries the dated decision.

Identity and tenancy were always **decoupled**, and tenancy is the half that survives. An
`Org` is a tenant boundary; an `OrgMembership` records who belongs to it. See the
[Data Model](data-model.md) for the fields.

- **Org isolation now binds the API, not the pages (AD-2, amended by Story 22.16).** Every
  API query still goes through `.for_org(org)`, because an API key genuinely pins one tenant
  (AD-8) and a programmatic caller must never see another org's jobs.

    The **pages** are deliberately cross-org: Job Status lists every organization with a
    column and a filter, and its rows open. That is not a reduction in real isolation — since
    Story 21.24 removed authentication, the org switcher accepted any non-ADMIN org from
    anyone, so another org's work was always two clicks away. The switcher made that a
    detour; listing it makes it honest. `get_all_jobs` / `get_any_job` serve the pages;
    `get_jobs` / `get_job` stay scoped for the API.

- **The organization is provenance (Story 22.16).** It is chosen on the upload form, recorded
  on the job, shown as a Job Status column, and written into the generated SBOM as its
  **supplier** (Story 22.14). It is no longer a mode the interface sits in — the header
  switcher is gone.

- **The acting org.** `get_request_org` resolves it, in one place, for both the pages and
  the API (AD-2). A presented API key wins and pins the caller to that key's org; otherwise
  a Django-admin session's org applies; otherwise the default org. The system ADMIN org is
  never the acting org (Story 2.18) — it is a platform tier, not a workspace.

- **Organizations are seeded, not created in the app (Story 22.10).** `seed_orgs` reads a
  committed `orgs.yml`, matching by slug because the slug is what the default-org setting and
  every API key reference. Removing a line deletes nothing.

- **Membership and the global-admin tier still exist as data**, and are still editable
  through `/api/v1/`. They no longer gate anything, their management screens were removed
  (Stories 22.9 and 22.11), and `OrgMembership.role` is read by nothing outside the
  membership services themselves. They are the seam host-supplied group claims re-attach to.

- **Per-org promote / demote.** Admins add or remove *per-org* admins with
  `promote_member_to_admin` (Story 2.16) and `demote_admin_to_member` (Story 2.20);
  an org may have any number of admins. Promotion adds an admin and demotes no one
  (replacing the old `transfer_admin`, which surprisingly demoted the caller and
  could strip a global admin). Demotion guards mirror the removal invariants — it
  cannot demote a global admin (they must stay admin of every org) or the org's
  last admin. These per-org roles are distinct from the global-admin tier below.

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
  the ADMIN org exists. The env-driven `seed_superuser` management command creates
  the initial superuser from `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD`
  on boot (idempotent, Story 2.13). The `bootstrap_admin_org` command is the
  idempotent catch-up path: it ensures the ADMIN org row is present and back-fills
  every existing superuser (covering superusers created before the hook, or before
  migrations ran). See [Setup](../developer/setup.md).

- **Global-admin management API.** `list_global_admins`,
  `grant_global_admin_by_email`, and `revoke_global_admin` back the global-admin
  screen (Story 13.1). Grant looks a user up by email (no auto-create); revoke
  removes them from the ADMIN org and demotes them to `member` everywhere, guarded
  so the last global admin can never be removed.

- **Non-stranding guards.** Because global admins are real memberships,
  membership-removal services (`remove_member` / `leave_org`) guard the tier: the
  ADMIN org can never lose its last member, and a global admin cannot be removed
  from a single normal org (they belong to all of them).

## Version-currency enrichment

The version-currency analysis phase (`analysis.services.versions`) reports how far
behind each dependency is, and reconciles two upstreams:

- **PyPI Latest.** Each component carries a **PyPI Latest** column alongside the
  installed version (Stories 8.22/8.23). When the installed version diverges from
  the latest, the divergence is flagged — and the flag is carried into the **Excel
  export as red text** so it stands out in a spreadsheet review.
- **conda-forge disambiguation.** The conda-forge latest is resolved via
  prefix.dev. Because many conda-forge feedstocks prefix the PyPI name with
  `python-` (e.g. `python-dateutil`), a reverse lookup disambiguates the
  `python-<name>` feedstock so the conda-forge latest matches the right package
  (Story 8.24).

The reconciled per-component versions feed both the in-app version report and the
Excel export; the pure comparison logic lives in the service layer (see the
[Code Reference](../developer/code-reference.md)).

## Dependency direction

The app dependency direction is one-way: `sbom → manifests`, and both depend on
`common`/`users`. The `sbom` app is the importer of the manifest upload service
(so the generate view lives in `sbom/views.py`). Keep new dependencies pointing the
same way to avoid import cycles.
