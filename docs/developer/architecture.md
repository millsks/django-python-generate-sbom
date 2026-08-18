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
- **AD-15 — Server-rendered UI.** Page views call the service layer directly and never
  the HTTP API. (This supersedes **AD-5**, which mandated a React SPA; Epic 21 reversed it.)
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
- **AD-13 — `src/` layout under a pixi umbrella** — `src/{config,django_service,django_apps}`
  with `tests/` at the root (see [Project Layout](project-layout.md)).
- **AD-16 — One reusable app.** All domain code is in `inventory`, imported unqualified.
- **AD-17 — No concrete `User` import.** App code uses `settings.AUTH_USER_MODEL` and
  `get_user_model()`; the concrete model is owned by the host project.

## Accounts, orgs, and the global-admin tier

Identity and tenancy are deliberately **decoupled**. A `User` is a standalone
account; an `Org` is a tenant boundary; an `OrgMembership` links the two with a
role (`admin` or `member`). See the [Data Model](data-model.md) for the fields.

- **Zero-org identity.** A freshly registered user has **no** memberships —
  registration creates the account only, never a "personal" org. Authentication
  is therefore independent of org membership. Anything org-scoped resolves the active
  org separately (`get_request_org`), and returns `None` when the user belongs to no
  org. `GET /auth/me/` exposes the same identity to API clients, returning
  `{id, email, is_admin, is_global_admin}` and succeeding for a user with no orgs.
  A signed-in user with no active org is **restricted to the home page** (Story 2.18):
  the nav hides the org-scoped destinations and the home page renders the shared
  no-org empty state instead of an error.

- **Admin authorization, gated twice.** Admin-only surfaces (Members, Organization,
  and the global-admin screen) are enforced at **both** layers (Story 2.17): page
  views mix in `OrgAdminRequiredMixin` / `GlobalAdminRequiredMixin` from
  `inventory/common/access.py`, and the matching API endpoints independently return
  `403` for a non-admin. Hiding a nav link is UX, not security. Admin-ness is
  **per-org** and re-evaluated against the active org, so switching org can change
  the answer.

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
  migrations ran). See [Setup](setup.md).

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
[Code Reference](code-reference.md)).

## Dependency direction

The app dependency direction is one-way: `sbom → manifests`, and both depend on
`common`/`users`. The `sbom` app is the importer of the manifest upload service
(so the generate view lives in `sbom/views.py`). Keep new dependencies pointing the
same way to avoid import cycles.
