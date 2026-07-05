# Data Model

The core relational models live across the Django apps. Tenant-scoped models inherit
from `OrgScopedModel` (AD-2), which carries the owning `Org` and enforces org
filtering.

## Accounts & tenancy (`users/`)

| Model | Purpose |
|---|---|
| `User` | Custom user (`AbstractUser` subclass); email is the login identifier, no username |
| `Org` | A tenant/organization; `is_admin_org` marks the one distinguished ADMIN org |
| `OrgMembership` | User ↔ Org link with a `Role` (`admin` or `member`) |
| `OrgApiKey` | Per-org API key, an `AbstractAPIKey` subclass (AD-8) |

`Org` is the tenancy boundary: every scoped record belongs to exactly one org, and
requests act within the caller's active org.

### Zero-org users

A `User` may have **zero** memberships. Registration creates the account only — no
"personal" org is auto-created — so identity is decoupled from tenancy. A user with
no orgs still authenticates (`GET /auth/me/`); org-scoped requests simply resolve no
active org until they join or create one.

### The ADMIN org and global admins

Exactly one org carries `is_admin_org=True` (the **ADMIN** org, seeded by a data
migration). Its members are **global admins**. A global admin is not a special flag
on `User`; instead they hold a real `OrgMembership(role=ADMIN)` row in the ADMIN org
**and** in every non-admin org (existing and future). So permission checks see them
as an ordinary admin of each org with no special-casing. `create_org` provisions all
global admins into a new org, and `grant_global_admin` back-fills a promoted admin
into every existing org. See [Architecture](architecture.md) for the tier's design.

## Manifests (`manifests/`)

| Model | Purpose |
|---|---|
| `ManifestUpload` | An uploaded dependency manifest (org-scoped) with a detected `Format` |

`Format` is a `TextChoices` covering the supported inputs (e.g. `requirements`,
`pyproject`, pixi and conda lockfiles). The concrete parsers live in
`sbom/parsers/`.

## Jobs (`sbom/`)

`SBOMJob` (org-scoped) is the heart of the system — one row per generation run.

| Field | Notes |
|---|---|
| `task_id` | UUID primary key; also the Celery task id |
| `manifest` | FK → `ManifestUpload` |
| `user` | FK → the submitting user |
| `status` | `PENDING → PROGRESS → SUCCESS`/`FAILED` — **written only by task code** (AD-12) |
| `progress` / `current_step` | Live progress for SPA polling |
| `output_format` | Internal serializer id for the SBOM |
| `result_key` | Storage key of the generated SBOM blob (not the blob itself, AD-6) |
| `summary_stats` | JSON roll-up for the results overview |
| `created_at` / `completed_at` | Timestamps |
| `artifacts_expire_at` | Drives scheduled artifact expiry |
| `failure_reason` | Set by the phase guard on failure |

## Analysis (`analysis/`)

| Model | Purpose |
|---|---|
| `AnalysisReport` | One enrichment result for a job |

Each report has a `report_type` (`vuln`, `license`, `graph`, `version`), an optional
`artifact_key` (blob in storage), and a JSON `summary`. A job has up to four reports —
one per analysis phase.

## Relationships

```mermaid
erDiagram
    Org ||--o{ OrgMembership : has
    User ||--o{ OrgMembership : in
    Org ||--o{ OrgApiKey : issues
    Org ||--o{ ManifestUpload : owns
    ManifestUpload ||--o{ SBOMJob : produces
    User ||--o{ SBOMJob : submits
    SBOMJob ||--o{ AnalysisReport : has
```

The `User`–`OrgMembership` edge is zero-or-many: a user may hold no memberships at
all. A **global admin** sits at the opposite extreme — one membership per org — via
real `OrgMembership(role=ADMIN)` rows fanned out across every org.
