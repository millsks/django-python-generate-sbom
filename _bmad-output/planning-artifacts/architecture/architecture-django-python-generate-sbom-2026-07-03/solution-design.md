---
name: django-python-generate-sbom
type: solution-design
status: draft
created: 2026-07-03
updated: 2026-07-03T14:00
binds: ARCHITECTURE-SPINE.md
---

# Solution Design — django-python-generate-sbom

## 1. System Overview

`django-python-generate-sbom` is a self-hosted Django web service that accepts Python dependency manifests and produces Software Bills of Materials (SBOMs) in three industry-standard formats, accompanied by four analysis reports: vulnerability scan, licence compliance, dependency graph, and version currency.

The system runs as a single Docker Compose stack. One Django/Gunicorn process serves the REST API and the pre-built React SPA. Two Celery workers drain separate queues: `pipeline` (parse → generate → persist) and `analysis` (vulnerability → licence → graph → version, running in parallel). Celery Beat manages 10-day artifact expiry. PostgreSQL is the durable system of record. Redis is the Celery broker and external API cache. MinIO (or S3 in production) stores artifact blobs.

### Design principles

| Principle | Where enforced |
|---|---|
| No inter-app HTTP — all cross-module calls are Python imports | AD-1 |
| Every model owning org data uses `OrgScopedModel`; all queries use `.for_org(org)` | AD-2 |
| Service layer accepts and returns plain Python objects only | AD-3 |
| Two Celery queues: `pipeline` and `analysis` | AD-4 |
| React SPA communicates only through the REST API | AD-5 |
| Pixi is the project-wide umbrella: one root `pixi.toml` installs Python + Node and orchestrates both `backend/` and `frontend/` tasks | AD-13 |
| Artifacts in S3; blobs never in PostgreSQL or Redis | AD-6 |
| Per-org concurrency gate checked before enqueue | AD-7 |
| API keys via `AbstractAPIKey` subclass (`djangorestframework-api-key`) | AD-8 |
| Graph API returns `{nodes, edges}` JSON; no PyVis HTML | AD-9 |
| `delay_on_commit()` for all Celery task dispatch from views | AD-10 |
| Artifact downloads as 303 → presigned S3 URL | AD-11 |
| `SBOMJob.status` written only by Celery task code | AD-12 |

---

## 2. Repository Layout

```
django-python-generate-sbom/               ← project root (pixi umbrella)
  pixi.toml                                ← umbrella: Python env + Node runtime + all tasks
  pixi.lock
  backend/                                 ← Django + Celery Python code
    config/
      settings/
        base.py          # shared settings — all apps, middleware, DRF, Celery
        local.py         # DEBUG=True, WhiteNoise, console email, MinIO
        production.py    # gunicorn, S3, HTTPS headers
      celery_app.py      # Celery app + Beat schedule
      urls.py            # /api/v1/ prefix, /health/, SPA catch-all
    <project_slug>/      # Django project package (project slug)
      users/             # Org, User, OrgMembership, OrgApiKey
      manifests/         # ManifestUpload, upload endpoint, format detection
      sbom/              # SBOMJob, generation pipeline, parsers/
        parsers/
          requirements.py
          pyproject.py
          pixi_lock.py   # PyYAML safe_load — pixi.lock is YAML despite .lock ext
          pixi_toml.py
          conda.py       # invokes conda/mamba solver (required runtime dep)
      analysis/          # AnalysisReport, four analysis services
        services/
          vulnerability.py  # OSV batch API
          license.py        # pip-licenses
          graph.py          # NetworkX → {nodes,edges} JSON + pygraphviz SVG
          versions.py       # PyPI JSON API + packaging
      tasks/
        sbom_pipeline.py # 8-phase chain (pipeline queue)
        analysis.py      # parallel group (analysis queue)
    tests/
      conftest.py        # shared fixtures
      unit/
        conftest.py
        test_parsers.py
        test_services.py
        test_views.py
        test_tasks.py
      integration/
        conftest.py      # real DB + broker='memory://' + test MinIO bucket
        test_pipeline.py
        test_analysis.py
        test_api.py
    manage.py
    pyproject.toml   # Python tool config + package metadata (pixi.toml is at the root)
    .env.example

  frontend/                                ← React 19 + MUI 9 + Vite 8 (project-root peer)
    src/
      api/               # all REST fetch calls — no direct fetch in components
        client.ts        # base client, Authorization header injection
        jobs.ts          # /sbom/generate/, /sbom/status/, /sbom/result/
        reports.ts       # /reports/vuln/, /reports/licenses/, /reports/graph/, /reports/versions/
        keys.ts          # /api-keys/ CRUD
        orgs.ts          # /orgs/ + /members/
      components/
        DepGraph.tsx     # Cytoscape.js wrapper (react-cytoscapejs + cytoscape-dagre)
        JobStatusBadge.tsx
        ProgressBar.tsx
      pages/
        UploadPage.tsx   # manifest upload + submit form
        ResultsPage.tsx  # tabs: SBOM · Vuln · Licences · Graph · Versions
        HistoryPage.tsx  # job history list
        KeysPage.tsx     # API key management
    dist/                # Vite build output — referenced by Django STATICFILES_DIRS
    package.json
    vite.config.ts

  docker-compose.yml
  README.md
  LICENSE
```

---

## 3. Django Application Modules

### 3.1 `users/`

**Models**

```python
class Org(models.Model):
    name: str          # display name
    slug: str          # URL-safe identifier, unique
    is_admin_org: bool # True for the ONE distinguished ADMIN org (global-admin tier)
    created_at: datetime

class OrgMembership(models.Model):
    org: FK(Org)
    user: FK(User)
    role: str          # 'admin' | 'member'
    # unique_together: (org, user)

class OrgApiKey(AbstractAPIKey):
    # inherits: prefix, hashed_key, name, created, revoked
    org: FK(Org)
    last_used_at: datetime | None
    revoked_at: datetime | None
```

**Org / admin / auth model (AD-14).** A `User` registers with **no** org (zero-org
identity) and gains access when a global admin creates an org (`create_org`) or an
admin adds them. Exactly one `Org` carries `is_admin_org=True` — the **ADMIN org** —
and its members are **global admins**: a cross-org superuser tier written as a real
`OrgMembership(role=admin)` into every non-admin org (existing and future), so no
authorization special-casing is needed (AD-2 org isolation is preserved). Identity is
served by `GET /api/v1/auth/me/` → `{id, email, is_admin, is_global_admin}`, decoupled
from the active org (which lives in the session and never resolves to the ADMIN org).
Per-org admins manage membership and **promote/demote** other admins (no *transfer*);
org creation and global-admin management are global-admin-gated. Admin authorization is
enforced at both the SPA route and the API (`403`).

`OrgApiKey.objects.get_from_key(raw_key)` is provided by `djangorestframework-api-key`. A custom DRF authentication class subclasses `APIKeyAuthentication`, updates `last_used_at` on each successful auth, and sets `request.auth = org_api_key`.

**Auth convention**

Two auth paths resolve to one active-org helper. The **machine API** carries the org
on `request.auth.org` (an `OrgApiKey`); the **web UI** (React SPA) authenticates by
session and carries the active org in the session. Views never read either directly —
they call `users/auth.py::get_request_org(request)`, which returns the acting org for
both paths (and **excludes the ADMIN org** from the session-resolved active org, AD-14),
so the "org is the first positional arg to every service" rule holds regardless of auth
mechanism. Admin-gated views use `get_admin_org(request)` (returns the org only if the
caller is an admin of it, else `None` → `403`).

```python
# API-key view (machine API):
org = request.auth.org
# Web-UI view (session): resolve uniformly, never from session/query-param directly:
org = get_request_org(request)          # any member
org = get_admin_org(request)            # admin-only actions; None → 403
```

**Services**

```python
# users/services.py
def register_user(email: str, password: str) -> User: ...          # zero-org (no org created)
def create_org(name: str, admin_user: User) -> Org: ...            # global-admin-gated at the view
def create_member(org: Org, email: str, role: str) -> User: ...    # add EXISTING user by email
def create_member_user(org: Org, email: str, temp_password: str, role: str) -> User: ...  # create NEW user
def remove_member(org: Org, user: User) -> None: ...
def promote_member_to_admin(org: Org, target: User) -> None: ...
def demote_admin_to_member(org: Org, target: User) -> None: ...    # inverse of promote (no transfer)
def leave_org(org: Org, user: User) -> None: ...
def create_api_key(org: Org, name: str) -> tuple[OrgApiKey, str]: ...
def revoke_api_key(org: Org, key_id: str) -> bool: ...
# global-admin tier
def is_global_admin(user: User) -> bool: ...
def get_the_admin_org() -> Org | None: ...
def grant_global_admin(user: User) -> None: ...                    # add to ADMIN org + admin of every org
def grant_global_admin_by_email(email: str) -> User: ...           # unregistered email -> NoSuchUserError
def revoke_global_admin(user: User) -> None: ...                   # remove from ADMIN org + demote everywhere; guards last global admin
def list_global_admins() -> list[User]: ...

# users/selectors.py
def get_user_orgs(user: User) -> QuerySet[Org]: ...
def get_org_members(org: Org) -> QuerySet[OrgMembership]: ...
def get_api_keys(org: Org) -> QuerySet[OrgApiKey]: ...
```

Membership operations raise domain errors (`NoSuchUserError`, `AlreadyMemberError`,
`EmailTakenError`, `LastAdminError`, `LastGlobalAdminError`, `GlobalAdminError`,
`AdminOrgProtectedError`, …) that views map to the standard `{"error", "code"}`
envelope.

---

### 3.2 `manifests/`

**Model**

```python
class ManifestUpload(OrgScopedModel):
    # OrgScopedModel adds: org (FK), objects = OrgScopedManager()
    user: FK(User)
    file_key: str      # S3 path: manifest-uploads/{org_id}/{upload_id}/{filename}
    detected_format: str  # 'requirements' | 'pyproject' | 'pixi_lock' | 'pixi_toml' | 'conda'
    original_filename: str
    uploaded_at: datetime
    # Provenance metadata (FR-3.8, all required) — embedded in SBOM metadata (§3.3)
    application_id: str        # free-text application identifier
    component_name: str        # component the manifest describes
    repository_url: str        # GitHub repo URL (URL-validated)
    source_branch: str         # branch the manifest came from
```

**Format detection** (applied in this order, not filename extension alone):

1. filename `pixi.lock` → `pixi_lock`
2. filename `pixi.toml` → `pixi_toml`
3. filename `pyproject.toml` + `[tool.poetry]` key → `pyproject` (Poetry)
4. filename `pyproject.toml` → `pyproject` (PEP 621)
5. filename `environment.yml` or `environment.yaml` → `conda`
6. filename matches `requirements*.txt` → `requirements`

**Endpoints**

| Method | Path | Action |
|---|---|---|
| `POST` | `/api/v1/manifests/upload/` | Upload file, detect format, store to S3, return `{upload_id, detected_format}` |
| `POST` | `/api/v1/sbom/generate/` | Concurrency gate → create `ManifestUpload` + `SBOMJob` → `delay_on_commit()` → 202 |

The generate endpoint lives in `manifests/views.py` per AD-7: this view owns both record creation and the concurrency gate, ensuring they run in the same transaction.

**Services**

```python
# manifests/services.py
def upload_manifest(org: Org, user: User, file_obj: IO[bytes], filename: str) -> ManifestUpload: ...

# manifests/selectors.py
def get_manifest(org: Org, upload_id: UUID) -> ManifestUpload: ...
```

---

### 3.3 `sbom/`

**Model**

```python
class SBOMJob(OrgScopedModel):
    task_id: UUID          # PK; also Celery task ID
    manifest: FK(ManifestUpload)
    user: FK(User)
    status: str            # 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILED'
    progress: int          # 0–100
    current_step: str      # phase name; displayed in UI
    output_format: str     # 'cyclonedx-json' | 'cyclonedx-xml' | 'spdx-json'
    result_key: str | None # S3 path: sbom-results/{org_id}/{task_id}/{filename}.{ext}
    summary_stats: dict    # {total_packages, direct, transitive, vulnerability_count, ...}
    created_at: datetime
    completed_at: datetime | None
    artifacts_expire_at: datetime | None
    failure_reason: str | None
```

**Status ownership** (AD-12): `status` is set to `PENDING` once — by `manifests/views.py` at job creation. All subsequent writes (`PROGRESS`, `SUCCESS`, `FAILED`) happen only in Celery task code via:

```python
# sbom/services.py
def update_job_status(task_id: UUID, status: str, progress: int = 0,
                      current_step: str = '', failure_reason: str | None = None) -> None: ...
def finalize_job(task_id: UUID, result_key: str, summary_stats: dict) -> None: ...
```

**Parsers** (`sbom/parsers/`)

Each parser implements:

```python
def parse(content: bytes) -> list[PackageSpec]:
    """Returns [{name, version, extras, markers}, ...]"""
```

For manifest-only formats (`pyproject.toml`, `requirements.txt`, `pixi.toml`), the parser calls `uv pip compile` as a subprocess to produce a full transitive closure. For lock files (`pixi.lock`), the parser reads the full resolved set directly. For `conda`/`conda environment.yml`, the parser invokes `conda env export` via the installed `conda`/`mamba` binary.

**SBOM generation** (`sbom/services.py`)

```python
def generate_sbom_document(
    packages: list[PackageSpec], output_format: str, metadata: SbomMetadata
) -> tuple[bytes, str]:
    """Returns (sbom_bytes, media_type)"""
    # CycloneDX JSON/XML → cyclonedx-python-lib
    # SPDX 2.3 JSON → lib4sbom
```

`metadata` carries the FR-3.8 provenance fields (application_id, component_name,
repository_url, source_branch) from the `ManifestUpload`, written into the SBOM's
document metadata:

- **CycloneDX 1.6**: `metadata.component` (`name` = component_name, `type` =
  `application`); an `externalReference` of type `vcs` = repository_url;
  `metadata.properties` `application:id` = application_id and `vcs:branch` =
  source_branch.
- **SPDX 2.3**: document / root package name = component_name; a VCS external
  reference = repository_url; application_id and source_branch as annotations /
  comments (best-effort — SPDX's metadata model is looser).

---

### 3.4 `analysis/`

**Model**

```python
class AnalysisReport(models.Model):
    job: FK(SBOMJob, related_name='reports')
    report_type: str       # 'vuln' | 'license' | 'graph' | 'version'
    artifact_key: str | None  # S3 path for downloadable artifact
    summary: dict          # report-type-specific summary JSON
    generated_at: datetime
    failed: bool
    failure_reason: str | None
```

**Chord envelope** — each analysis task returns this exact shape; the chord callback reads it to populate `AnalysisReport`:

```python
{
    "report_type": "vuln",        # | "license" | "graph" | "version"
    "artifact_key": "sbom-results/{org_id}/{task_id}/vuln.json",  # or null
    "summary": { ... },           # report-type-specific summary
    "failed": False,
    "failure_reason": None,       # str if failed is True
}
```

**Vulnerability service** (`analysis/services/vulnerability.py`)

Calls `POST https://api.osv.dev/v1/querybatch` with packages batched in groups of 1000. Each package is sent as `{"package": {"name": name, "ecosystem": "PyPI"}, "version": version}`. Responses are enriched with CWE data from the NVD API. Results cached in Redis for 24 hours via `requests-cache`. Rate limited to 1 req/s via `requests-ratelimiter`. Retried up to 3 times with exponential backoff via `tenacity`.

**Licence service** (`analysis/services/license.py`)

Uses `pip-licenses --from=mixed --format=json` output for installed packages. Classifies each licence into one of four tiers:

| Tier | Examples | Action signalled |
|---|---|---|
| Strong Copyleft | GPL, AGPL | Attention required |
| Weak Copyleft | LGPL, MPL | Review recommended |
| Unknown | No SPDX ID, proprietary | Legal review needed |
| Permissive | MIT, Apache 2.0, BSD | Use freely |

**Graph service** (`analysis/services/graph.py`)

Builds a NetworkX `DiGraph` from the resolved package list. Produces two outputs:

1. `{nodes, edges}` JSON (stored in `AnalysisReport.summary`) — served at `GET /api/v1/sbom/result/{task_id}/reports/graph/` and consumed directly by Cytoscape.js in the React SPA.
2. A Graphviz SVG (generated via `pygraphviz`) — stored in S3 at `sbom-results/{org_id}/{task_id}/graph.svg` and available for download.

Graph API response shape required by Cytoscape.js:

```json
{
  "nodes": [
    {"data": {"id": "requests==2.32.3", "label": "requests", "version": "2.32.3"}}
  ],
  "edges": [
    {"data": {"source": "requests==2.32.3", "target": "urllib3==2.3.0"}}
  ]
}
```

**Version currency service** (`analysis/services/versions.py`)

Fetches `/pypi/{package}/json` from the PyPI JSON API (cached 1 hour in Redis via `requests-cache`). Compares installed version to latest using PEP 440 sort via the `packaging` library. Classifies currency by release series distance:

| Classification | Condition |
|---|---|
| Current | installed == latest |
| Patch behind | same major.minor, lower patch |
| Minor behind | same major, lower minor |
| Major behind | lower major |
| Pre-release | installed version is pre-release |

LTS version registry for Django and Python is configurable via `SBOM_LTS_REGISTRY` env var (JSON file path or inline JSON); defaults ship with the service.

---

## 4. Celery Pipeline

### 4.1 Canvas pattern

```python
# tasks/sbom_pipeline.py
from celery import chain, group, shared_task

pipeline = chain(
    detect_and_parse_manifest.si(manifest_key, org_id, task_id),
    resolve_transitive_deps.s(),
    generate_sbom_document.s(output_format),
    group(
        scan_vulnerabilities.s(),
        analyze_licenses.s(),
        build_dependency_graph.s(),
        check_version_currency.s(),
    ) | aggregate_analysis_results.s(),
    persist_artifacts.s(),
)
```

All tasks use `@shared_task` — no Celery app import in task modules.

### 4.2 Phase breakdown

| Phase | Queue | Progress | What happens |
|---|---|---|---|
| 1 — detect & parse | `pipeline` | 0 → 15% | Download manifest from S3; detect format; call appropriate parser |
| 2 — resolve transitive | `pipeline` | 15 → 40% | `uv pip compile` or lock-file read; expand to full package list |
| 3 — generate SBOM | `pipeline` | 40 → 55% | `cyclonedx-python-lib` or `lib4sbom`; produce bytes in requested format |
| 4 — vulnerability scan | `analysis` | 55 → 80% | OSV batch API + NVD CWE enrichment |
| 5 — licence compliance | `analysis` | 80 → 88% | `pip-licenses` classification into four tiers |
| 6 — dependency graph | `analysis` | 88 → 93% | NetworkX DAG → JSON + pygraphviz SVG |
| 7 — version currency | `analysis` | 93 → 97% | PyPI JSON API + PEP 440 comparison |
| 8 — persist artifacts | `pipeline` | 97 → 100% | Upload all artifacts to S3; write `result_key`; set status SUCCESS |

### 4.3 Progress signalling

```python
task.update_state(state='PROGRESS', meta={'progress': N, 'current_step': '<phase name>'})
```

The React SPA polls `GET /api/v1/sbom/status/{task_id}/` every 5 seconds via the `useJobStatus(taskId)` hook, which reads `SBOMJob.progress` and `SBOMJob.current_step` from PostgreSQL (Celery result backend writes progress there via the `update_job_status` service function).

### 4.4 Error handling

- `SoftTimeLimitExceeded` caught in the chain header: job set to `FAILED`, reason surfaced to user, no partial SBOM written.
- Analysis task failures do not abort the chord. Each task returns `failed: True` in its envelope; the chord callback writes `AnalysisReport.failed = True` and continues.
- Tasks retry on transient external API errors (OSV, PyPI) up to 3 times via `tenacity` before marking the analysis report as failed.

### 4.5 Celery Beat — artifact cleanup

```python
# backend/config/celery_app.py
app.conf.beat_schedule = {
    'expire-artifacts': {
        'task': 'tasks.sbom_pipeline.expire_artifacts_task',
        'schedule': crontab(hour=3, minute=0),   # nightly at 03:00
        'options': {'queue': 'pipeline'},
    },
}
```

Cleanup selector:

```python
SBOMJob.objects.filter(
    artifacts_expire_at__lte=now(),
    result_key__isnull=False,
)
```

For each matched job: delete all S3 objects under `sbom-results/{org_id}/{task_id}/`; null `result_key` on the job; null `artifact_key` on all related `AnalysisReport` rows. Job record is never deleted.

---

## 5. REST API

### 5.1 Authentication

All API requests carry `Authorization: Api-Key <raw_key>`. Unauthenticated requests → `401`. The custom auth class (`OrgApiKeyAuthentication`) calls `OrgApiKey.objects.get_from_key(raw_key)`, updates `last_used_at`, and sets `request.auth = org_api_key`.

### 5.2 Endpoint inventory

Auth column: **Api-Key** = machine API (`Authorization: Api-Key`); **Session** = web-UI
(React SPA) session auth; **No** = unauthenticated. Account and org-management endpoints
are session-authenticated and admin-gated server-side (`403`) per AD-14.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health/` | No | Docker health check; returns `{"status": "ok"}` |
| `POST` | `/api/v1/auth/register/` | No | Register a **zero-org** user (returns `org: null`) |
| `POST` | `/api/v1/auth/login/` | No | Exchange email+password for a session; set the active org (web UI) |
| `POST` | `/api/v1/auth/logout/` | Session | Invalidate the session |
| `GET` | `/api/v1/auth/me/` | Session | Current user identity `{id, email, is_admin, is_global_admin}` (AD-14) |
| `GET` | `/api/v1/orgs/` | Session | List the user's orgs (active flagged; ADMIN org excluded) |
| `POST` | `/api/v1/orgs/create/` | Session | Create an org (**global admin only** → `403`) |
| `POST` | `/api/v1/orgs/switch/` | Session | Switch the active org |
| `GET` | `/api/v1/orgs/me/` | Session | Current active org |
| `POST` | `/api/v1/orgs/leave/` | Session | Leave the active org (guards sole/global admin) |
| `GET` | `/api/v1/orgs/members/` | Session | List active-org members (**admin only**) |
| `POST` | `/api/v1/orgs/members/` | Session | Add an **existing** user by email (admin only; `no_such_user` if unregistered) |
| `POST` | `/api/v1/orgs/members/create-user/` | Session | Create a **new** user account + add them (admin only; `email_taken` if exists) |
| `DELETE` | `/api/v1/orgs/members/{user_id}/` | Session | Remove a member (admin only) |
| `POST` | `/api/v1/orgs/promote-admin/` | Session | Promote a member to admin (admin only) |
| `POST` | `/api/v1/orgs/demote-admin/` | Session | Demote an admin to member (admin only; guards last/global admin) |
| `GET` | `/api/v1/admin/global-admins/` | Session | List global admins (**global admin only**) |
| `POST` | `/api/v1/admin/global-admins/` | Session | Grant global admin by email (global admin only; `no_such_user` if unregistered) |
| `DELETE` | `/api/v1/admin/global-admins/{user_id}/` | Session | Revoke global admin — remove from ADMIN org + demote everywhere (global admin only; blocked on last global admin) |
| `GET` | `/api/v1/api-keys/` | Api-Key | List API keys for org |
| `POST` | `/api/v1/api-keys/` | Api-Key | Create API key |
| `DELETE` | `/api/v1/api-keys/{id}/` | Api-Key | Revoke API key |
| `POST` | `/api/v1/manifests/upload/` | Yes | Upload manifest file |
| `POST` | `/api/v1/sbom/generate/` | Yes | Submit SBOM job (concurrency gate → 202) |
| `GET` | `/api/v1/sbom/status/{task_id}/` | Yes | Poll job status + progress |
| `GET` | `/api/v1/sbom/result/{task_id}/` | Yes | 303 → presigned S3 URL for SBOM artifact |
| `GET` | `/api/v1/sbom/jobs/` | Yes | List org jobs (paginated) |
| `GET` | `/api/v1/sbom/result/{task_id}/reports/vuln/` | Yes | Vulnerability report JSON |
| `GET` | `/api/v1/sbom/result/{task_id}/reports/licenses/` | Yes | Licence report JSON |
| `GET` | `/api/v1/sbom/result/{task_id}/reports/graph/` | Yes | Dependency graph `{nodes, edges}` JSON |
| `GET` | `/api/v1/sbom/result/{task_id}/reports/versions/` | Yes | Version currency report JSON |

### 5.3 Standard response shapes

**202 response (job accepted)**

```json
{
  "task_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "PENDING",
  "status_url": "/api/v1/sbom/status/3fa85f64.../",
  "estimated_seconds": 45
}
```

**Status poll response**

```json
{
  "task_id": "3fa85f64...",
  "status": "PROGRESS",
  "progress": 62,
  "current_step": "vulnerability scan",
  "created_at": "2026-07-03T14:00:00Z",
  "completed_at": null
}
```

**Error envelope**

```json
{
  "error": "Manifest format not recognised",
  "code": "unsupported_format"
}
```

**Pagination envelope**

```json
{
  "count": 47,
  "next": "/api/v1/sbom/jobs/?page=2",
  "previous": null,
  "results": [...]
}
```

`page_size` default 25, max 100 via `?page_size=`.

### 5.4 Concurrency gate (AD-7)

Before creating `SBOMJob`:

```python
active = SBOMJob.objects.for_org(org).filter(
    status__in=['PENDING', 'PROGRESS']
).count()
if active >= settings.SBOM_MAX_CONCURRENT_JOBS_PER_ORG:
    return Response(
        {"error": "Concurrent job limit reached", "code": "rate_limited"},
        status=429,
        headers={"Retry-After": "60"},
    )
```

`SBOM_MAX_CONCURRENT_JOBS_PER_ORG` defaults to `5`, set via env var.

---

## 6. Storage

### 6.1 Storage paths

| Object | S3 path |
|---|---|
| Uploaded manifest | `manifest-uploads/{org_id}/{upload_id}/{original_filename}` |
| SBOM artifact | `sbom-results/{org_id}/{task_id}/sbom.{ext}` |
| Vulnerability report | `sbom-results/{org_id}/{task_id}/vuln.json` |
| Licence report | `sbom-results/{org_id}/{task_id}/licenses.json` |
| Dependency graph (SVG) | `sbom-results/{org_id}/{task_id}/graph.svg` |
| Version report | `sbom-results/{org_id}/{task_id}/versions.json` |

### 6.2 Presigned URL download flow (AD-11)

```
Client → GET /api/v1/sbom/result/{task_id}/ → Django view
Django view → SBOMJob.objects.for_org(org).get(task_id=task_id)  # 404 if not found
Django view → default_storage.url(result_key)  # generates presigned URL (24h TTL)
Django view → 303 See Other (Location: presigned-url)
Client → GET presigned-url → S3/MinIO → artifact bytes
```

Django never reads or proxies artifact bytes. The same code path works in local dev (MinIO) and production (AWS S3) — `django-storages` handles both.

### 6.3 Redis usage

| Key pattern | TTL | Content |
|---|---|---|
| `celery-task-meta-{task_id}` | Celery default (24h) | Task result metadata |
| `osv-cache:{package}:{version}` | 24 hours | OSV vulnerability response |
| `pypi-cache:{package}` | 1 hour | PyPI JSON API response |

No artifact content is ever written to Redis.

---

## 7. Frontend Architecture

### 7.1 Technology stack

| Library | Version | Role |
|---|---|---|
| React | 19.2.7 | SPA framework |
| @mui/material | 9.1.2 | Component library |
| Vite | 8.1.3 | Build tool |
| cytoscape | 3.34.0 | Graph rendering engine |
| react-cytoscapejs | 2.0.0 | React wrapper for Cytoscape |
| cytoscape-dagre | 4.0.0 | Hierarchical layout for dependency graph |

### 7.2 Page structure

| Route | Component | Description |
|---|---|---|
| `/` | `UploadPage` | Drag-and-drop manifest upload; format selector; job submission |
| `/results/:taskId` | `ResultsPage` | Tabs: SBOM · Vulnerability · Licences · Graph · Versions |
| `/history` | `HistoryPage` | Paginated list of past jobs linking to `ResultsPage` |
| `/keys` | `KeysPage` | Create, list, revoke API keys |

`ResultsPage` uses the `useJobStatus(taskId)` hook to poll `/api/v1/sbom/status/{taskId}/` every 5 seconds until `status` is `SUCCESS` or `FAILED`. On success it fetches each report tab's data in parallel.

### 7.3 Dependency graph panel

`DepGraph.tsx` wraps `react-cytoscapejs` and applies the `dagre` layout. Data is fetched from `GET /api/v1/sbom/result/{taskId}/reports/graph/` and passed directly to Cytoscape as:

```tsx
<CytoscapeComponent
  elements={CytoscapeComponent.normalizeElements({
    nodes: graphData.nodes,
    edges: graphData.edges,
  })}
  layout={{ name: 'dagre', rankDir: 'TB' }}
  style={{ width: '100%', height: 600 }}
/>
```

No iframe, no PyVis HTML.

### 7.4 Static serving

Vite builds to `frontend/dist/` (at the project root). `backend/config/settings/base.py` sets `STATICFILES_DIRS = [BASE_DIR.parent.parent / 'frontend' / 'dist']` so Django can see the built assets. In Docker Compose, a shared volume (or multi-stage Dockerfile) makes `frontend/dist/` available to the Django container before `collectstatic` runs. `collectstatic` copies assets into `STATIC_ROOT`; WhiteNoise serves them under `/static/`. Django's SPA catch-all URL (`re_path(r'^(?!api/|health/).*$', SpaView.as_view())`) serves `index.html` for all non-API routes, enabling React Router's browser history mode.

---

## 8. Configuration

All runtime configuration is via environment variables read by `django-environ`. No secrets are committed.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | Django secret key (required) |
| `DEBUG` | `False` | Enable Django debug mode |
| `ALLOWED_HOSTS` | `localhost` | Comma-separated allowed host names |
| `DATABASE_URL` | — | PostgreSQL DSN |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis DSN (broker + cache) |
| `AWS_STORAGE_BUCKET_NAME` | — | S3 or MinIO bucket name |
| `AWS_S3_ENDPOINT_URL` | — | MinIO endpoint (local dev) |
| `AWS_ACCESS_KEY_ID` | — | S3/MinIO key |
| `AWS_SECRET_ACCESS_KEY` | — | S3/MinIO secret |
| `SBOM_MAX_CONCURRENT_JOBS_PER_ORG` | `5` | Per-org concurrency gate limit |
| `SBOM_LTS_REGISTRY` | built-in | Path to LTS registry JSON file or inline JSON |
| `CELERY_TASK_SOFT_TIME_LIMIT` | `1800` | Soft time limit per task (seconds) |
| `CELERY_TASK_TIME_LIMIT` | `2100` | Hard time limit per task (seconds) |

---

## 9. Docker Compose

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

---

## 10. Security Design

### Org isolation

`OrgScopedModel` adds an `org` FK to every model. `OrgScopedQuerySet.for_org(org)` adds `.filter(org=org)` to all queries. Every service function that touches org-owned data takes `org` as its first positional argument. Views extract org as `request.auth.org` and pass it through — there is no path to cross-org data access through normal code flow.

API endpoints return `404` for cross-org access (the queryset simply returns no row — `DoesNotExist` is indistinguishable from "does not exist"). Web UI routes return `403` for authenticated users (UUID URLs don't leak existence; `403` gives clearer UX for shared-link scenarios).

### Admin authorization and the global-admin tier (AD-14)

Two admin scopes exist. A **per-org admin** (`OrgMembership(role=admin)`) manages that
org's membership, promotions/demotions, and API keys. A **global admin** (a member of
the one `is_admin_org` org) is provisioned as a real admin membership in every non-admin
org and additionally may create orgs and grant/revoke global admin. Every admin-only
capability is enforced at **two independent layers**: the React SPA hides admin routes
and affordances using the `is_admin` / `is_global_admin` flags from `auth/me`, and each
admin-only API view re-checks authorization server-side (`get_admin_org` /
`is_global_admin`), returning `403` (`not_admin` / `not_global_admin`) regardless of the
client — UI hiding is never the only gate. Because a global admin holds an ordinary
`role=admin` membership everywhere, no authorization path special-cases them, and AD-2's
org isolation is never bypassed. Membership invariants (org keeps ≥1 admin; the ADMIN org
keeps ≥1 global admin; a global admin cannot be stranded/removed from a single org) are
enforced in the service layer and surfaced as `{"error", "code"}` domain errors.

### API key security

`djangorestframework-api-key` generates a random 32-byte key, stores the SHA-512 hash, and returns the plaintext once at creation time. SHA-512 is appropriate for random tokens (fast comparison is acceptable; PBKDF2 is for passwords). The `OrgApiKey.revoked_at` field enables soft revocation that preserves audit history.

### Credentials

No API keys, passwords, or secrets are logged. The `structlog` configuration explicitly excludes `Authorization` headers from request log entries. `.env` files are in `.gitignore`.

### Input validation

Uploaded files are validated for supported formats before parsing. Subprocess calls to `uv pip compile` and `conda`/`mamba` receive file paths, never unsanitised content as shell arguments.

---

## 11. Observability

All logging uses `structlog` with JSON renderer. Every log entry binds `org_id`, `task_id` (where applicable), and `user_id` as structured fields. Log levels:

| Level | When |
|---|---|
| `info` | Job lifecycle events (created, phase start, completed) |
| `warning` | Retried external API calls, partial analysis failures |
| `error` | Task failure, unexpected exceptions (before re-raise) |

`structlog` is configured in `config/settings/base.py` with `JSONRenderer` for production. `ConsoleRenderer` may be used in local dev.

---

## 12. Open Items (Deferred to Stories)

- Frontend state management library choice (React Query vs Zustand vs Redux) — constrained only by the `frontend/src/api/` convention
- Per-app URL routing patterns — constrained only by `/api/v1/` prefix
- Model field indexes — constrained only by the ERD relationship shape
- Celery worker `--concurrency` settings — operator choice documented in README
- Nginx vs WhiteNoise-only for production static serving — operator choice
- SPDX 3.0 output — add serializer in `sbom/services.py` when `lib4sbom` stabilises
- `uv.lock` / `poetry.lock` parsers — add modules to `sbom/parsers/` with no structural change
- WebSocket / Django Channels for real-time progress — polling is the baseline; Channels is a drop-in upgrade
- OAuth / SSO — plugs into DRF auth class layer; AD-8's key model unchanged
