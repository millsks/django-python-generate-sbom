---
stepsCompleted: ["step-01", "step-02", "step-03", "step-04"]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-django-python-generate-sbom-2026-07-03/prd.md
  - _bmad-output/planning-artifacts/prds/prd-django-python-generate-sbom-2026-07-03/addendum.md
  - _bmad-output/planning-artifacts/architecture/architecture-django-python-generate-sbom-2026-07-03/ARCHITECTURE-SPINE.md
---

# django-python-generate-sbom - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for django-python-generate-sbom, decomposing the requirements from the PRD and Architecture spine into implementable stories. No UX design contract exists for this project.

## Requirements Inventory

### Functional Requirements

**F1 — Account and Org Management**

FR-1.1: A new user registers with an email address and password. Registration creates a personal org named after the user.
FR-1.2: A registered user can create additional orgs, becoming the admin of each created org.
FR-1.3: An org admin can add a new member by creating an account on their behalf: entering the new member's email address and a temporary password. The admin shares these credentials out-of-band. No email infrastructure required.
FR-1.4: An org admin can remove a member from the org. Removed members lose access to all org resources immediately.
FR-1.5: An org admin can transfer admin privileges to another member. The org must always have at least one admin.
FR-1.6: A user can switch between orgs they belong to within the web UI. The active org determines which jobs and API keys are visible.
FR-1.7: A user can leave an org they do not own. The org is not deleted.

**F2 — API Key Management**

FR-2.1: An org admin can create a named API key scoped to the org. The full key value is shown exactly once at creation; subsequent views show only the key prefix (first 8 characters) plus a masked suffix.
FR-2.2: An org may have up to 10 active API keys simultaneously.
FR-2.3: An org admin can revoke any API key. Revocation takes effect immediately; in-flight requests authenticated with that key complete normally.
FR-2.4: The web UI lists all active API keys for the org, showing name, creation date, last-used date, and prefix.
FR-2.5: API requests are authenticated by passing the key in the `Authorization: Api-Key <key>` header. A revoked or invalid key returns `401`.
FR-2.6: All API endpoints that return or modify org data enforce that the authenticated key belongs to the org owning the requested resource.

**F3 — Manifest Upload and Job Submission**

FR-3.1: A user submits a SBOM generation job by uploading a single manifest or lock file via the web UI or `POST /api/v1/sbom/generate/`.
FR-3.2: Accepted file formats for v1: `requirements.txt`, `pyproject.toml`, `pixi.lock`, `pixi.toml`, `conda environment.yml`. Unsupported formats return `400` with a clear error listing supported formats.
FR-3.3: The system automatically detects the manifest format from filename and structural markers. If detection is ambiguous, the user may specify the format explicitly via an optional `manifest_format` parameter.
FR-3.4: Uploaded manifest files are validated before queuing: MIME type checked, file size must not exceed 50 MB, content parsed with safe loaders only (no `eval`, no `exec`). Invalid files rejected with `400` before a task is enqueued.
FR-3.5: On successful submission the system returns `202 Accepted` with a `task_id`, `status_url`, and `estimated_seconds`. The manifest file and connection are released immediately; processing continues asynchronously.
FR-3.6: The user selects the SBOM output format at submission time. Accepted values: `cdx-json` (default), `cdx-xml`, `spdx-2.3`. SPDX 3.0 is out of scope for v1.
FR-3.7: The job record is owned by the submitting org. A user submitting under Org A cannot see or interact with the same job when acting under Org B.

**F4 — SBOM Generation Pipeline**

FR-4.1: Each submitted job is processed by an asynchronous Celery pipeline. The pipeline executes in eight phases with progress reported at each phase boundary (0–100%).
FR-4.2: Phase sequence: (1) Detect & parse manifest 0–15%, (2) Resolve transitive dependencies 15–40%, (3) Generate SBOM document 40–55%, (4) Vulnerability scan 55–80%, (5) License compliance analysis 80–88%, (6) Dependency graph generation 88–93%, (7) Version currency analysis 93–97%, (8) Persist artifacts 97–100%. Phases 4–7 run in parallel; pipeline waits for all four before Phase 8.
FR-4.3: Transitive dependency resolution by format: `pixi.lock` → PyYAML safe loader (lock file contains full tree); `pixi.toml` → TOML parse + `uv pip compile` subprocess; `pyproject.toml` → `tomllib` + `uv pip compile` if no lock; `requirements.txt` → `packaging.requirements.Requirement` + `uv pip compile`; `conda environment.yml` → PyYAML + `conda`/`mamba` solver (required runtime dependency; job fails with descriptive error if solver absent).
FR-4.4: SBOM generated from resolved package list using `cyclonedx-python-lib` (CycloneDX) or `lib4sbom` (SPDX). Format selection determines which serializer is invoked.
FR-4.5: Phase 3 failure → job fails entirely. Phases 4–7 failure → job completes with partial result; SBOM available; UI indicates which analysis reports are unavailable with failure reason.
FR-4.6: 25-minute soft limit triggers `SoftTimeLimitExceeded` → task catches exception, marks job `FAILED` with reason `"soft_timeout"`, releases resources, no partial SBOM returned. 30-minute hard limit forcibly terminates worker; job marked `FAILED` with reason `"hard_timeout"` by cleanup sweep. Both reasons surfaced to user.
FR-4.7: Client polls `GET /api/v1/sbom/status/{task_id}/` to retrieve status (`PENDING`, `PROGRESS`, `SUCCESS`, `FAILURE`), progress percentage (0–100), current phase name, and — on success — a `result_url`.

**F5 — Analysis Reports**

FR-5.1: Vulnerability Report — queries OSV batch API (`POST https://api.osv.dev/v1/querybatch`) with all resolved packages. Report lists each vulnerable package with CVE/GHSA identifier(s), CVSS score and severity (Critical/High/Medium/Low), CWE classification (enriched from NVD where OSV data is absent), and advisory link.
FR-5.2: License Compliance Report — extracts declared license for each package from PyPI metadata. Packages grouped into four tiers in descending attention order: Strong Copyleft (AGPL/GPL), Weak Copyleft (LGPL), Unknown (no/non-SPDX license), Permissive (all other SPDX).
FR-5.3: Dependency Graph — builds directed acyclic graph (DAG) using NetworkX. Phase 6 produces two outputs: `{nodes, edges}` JSON for interactive React view (Cytoscape.js) and a static Graphviz SVG artifact for download.
FR-5.4: Version Currency Report — fetches latest stable version from PyPI JSON API; classifies installed version by release series distance: `current`, `behind-1`, `behind-2+`, or `unknown`. LTS-aware classification for Django and Python. LTS registry configurable via `SBOM_LTS_REGISTRY` env var (JSON mapping).
FR-5.5: External API caching in Redis: PyPI JSON API responses cached 1-hour TTL; OSV API responses cached 24-hour TTL. Cache keys scoped by package name + version; shared safely across orgs for the same package+version pair.

**F6 — Results Web UI**

FR-6.1: On job completion, results page presents output in five tabs: Overview, Vulnerabilities, Licenses, Dependency Graph, Version Currency.
FR-6.2: Overview tab — summary statistics: total package count, vulnerable package count, license category breakdown, packages at current/behind/unknown versions, SBOM download button, links to each analysis tab.
FR-6.3: Vulnerabilities tab — sortable table: package name, installed version, CVE/GHSA IDs, CVSS score, severity, advisory link. Filterable by severity. Zero-finding state displayed explicitly.
FR-6.4: Licenses tab — packages grouped into four tiers (Strong Copyleft, Weak Copyleft, Unknown, Permissive) in that order. Each package links to PyPI page. Tiers with zero packages collapsed by default.
FR-6.5: Dependency Graph tab — interactive graph rendered with Cytoscape.js and hierarchical dagre layout. Supports zoom, pan, node drag, and hover-to-highlight. "Download SVG" button exports the static Graphviz artifact.
FR-6.6: Version Currency tab — table of all packages with installed version, latest version, currency status badge (Current/Behind/Unknown). Sortable by status. Packages classified `behind-2+` displayed first by default.
FR-6.7: If any analysis phase failed (per FR-4.5), the corresponding tab displays a failure notice with the error reason. The SBOM download and successful report tabs remain available.
FR-6.8: Results page URL is stable and shareable within the org. Any member of the same org with the URL can view the results. Users outside the org receive `403`.

**F7 — Job History Dashboard**

FR-7.1: Job history dashboard lists all SBOM generation jobs for the active org, most recent first, with columns: submitted time, manifest filename, manifest format, output format, status (with visual indicator), and a link to results.
FR-7.2: In-progress jobs display current progress percentage and phase name, updated via JavaScript polling of `GET /api/v1/sbom/status/{task_id}/` every 5 seconds.
FR-7.3: Jobs in `FAILED` state display a failure reason summary in the list.
FR-7.4: Dashboard supports filtering by status (All/In Progress/Completed/Failed) and manifest format.
FR-7.5: Job list paginated at 25 jobs per page.

**F8 — Artifact Retention and Cleanup**

FR-8.1: All generated artifacts (SBOM files, analysis report files) automatically deleted 10 days after the job completed. Job record and metadata (status, package count, summary statistics) retained indefinitely.
FR-8.2: Scheduled Celery Beat job runs daily to delete expired artifacts. Deletion cascades to storage backend and clears artifact key from the job record.
FR-8.3: On the results page and job history, expired jobs display a notice that artifacts are no longer available, with the expiry date. Job record remains visible.
FR-8.4: A user can manually delete a job's artifacts before the 10-day TTL. Job record is retained.
FR-8.5: Org admins can bulk-delete all artifacts for the org.

### NonFunctional Requirements

NFR-1.1: Every data model that stores org-owned data includes an `org` foreign key. All ORM queries filtered by authenticated org. Cross-org direct-object-reference attacks return `404`, not `403`, to avoid leaking existence information.
NFR-1.2: Redis result backend stores task state under keys prefixed `{org_id}:{task_id}`. Artifact storage paths follow `sbom-results/{org_id}/{task_id}/{filename}`.
NFR-2.1: Pipeline completion times (single Celery worker, 4 cores): <50 packages <35s; 50–250 packages <135s; 250–1000 packages <7 min; 1000+ packages <25 min.
NFR-2.2: Web UI results page must load (excluding graph rendering) in under 3 seconds once artifacts are available.
NFR-3.1: Manifest files parsed using safe loaders only (`tomllib`, `PyYAML` safe load). No manifest content passed to `eval`, `exec`, or shell without sanitization.
NFR-3.2: Generated artifact URLs are presigned (S3) or session-authenticated (local). No artifact publicly accessible without authentication.
NFR-3.3: API keys stored as SHA-512-hashed values via `djangorestframework-api-key` (AbstractAPIKey). Plaintext key shown once at creation.
NFR-3.4: File uploads validated for MIME type and file size before acceptance. Zip bombs and path traversal attempts rejected.
NFR-4.1: Per-org concurrent job limit configurable via `SBOM_MAX_CONCURRENT_JOBS_PER_ORG` (default 5). Submissions beyond the active limit return `429` with a `Retry-After` header.
NFR-4.2: External API calls (OSV, PyPI JSON) rate-limited via `requests-ratelimiter`: 1 req/s for OSV, 5 req/s for PyPI.
NFR-5.1: Distributed as a Docker Compose application. `docker compose up` from a cloned repository with a configured `.env` file starts the full stack.
NFR-5.2: All configuration driven by environment variables. No secrets committed to the repository.
NFR-5.3: Structured logging via `structlog` in JSON format. All log entries include `org_id`, `task_id` (where applicable), and `user_id`.
NFR-5.4: Project licensed under Apache 2.0.
NFR-6.1: Each pipeline phase emits a structured log entry on start and completion, including phase name, duration, and package count processed.
NFR-6.2: Celery task failures logged with full traceback and the manifest format that triggered the failure.

### Additional Requirements

**From Architecture Spine (AD constraints that affect story implementation):**

- [AD-1] All cross-app calls are direct Python imports from the target app's `services.py` or `selectors.py`. No `requests` calls to localhost. No shared task queues as a coupling mechanism.
- [AD-2] Every model owning org data extends `OrgScopedModel` (abstract base with `org` FK + `OrgScopedQuerySet.for_org(org)`). API endpoints return `404` for cross-org access; Web UI routes return `403`. Org always the first positional parameter of any service/selector touching org-owned data.
- [AD-3] Service functions (`services.py` / `selectors.py`) accept and return plain Python objects only — no `HttpRequest`, `Response`, or Celery `Task` instance. Same service callable from DRF view and Celery task.
- [AD-4] Phases 1–3 and Phase 8 route to the `pipeline` Celery queue. Phases 4–7 route to the `analysis` queue. Celery Beat cleanup tasks also route to `pipeline`. Two separate worker processes, one per queue.
- [AD-5] React SPA in `frontend/` at project root built to `frontend/dist/`. Django's `STATICFILES_DIRS` = `[BASE_DIR.parent.parent / 'frontend' / 'dist']` in `backend/config/settings/base.py`. WhiteNoise serves the built SPA. All data flows through `/api/v1/`. No Django template coupling.
- [AD-6] PostgreSQL = durable models. Redis = transient broker messages, task result metadata, TTL-cached external API responses. S3/MinIO = all binary artifact blobs. Artifact keys (not blobs) stored in `SBOMJob.result_key` and `AnalysisReport.artifact_key`.
- [AD-7] Concurrency gate in `manifests/views.py` before enqueue: count `PENDING`/`PROGRESS` jobs for org; return `429` with `Retry-After` if at or above `settings.SBOM_MAX_CONCURRENT_JOBS_PER_ORG`.
- [AD-8] `OrgApiKey` extends `AbstractAPIKey` from `djangorestframework-api-key`. Adds `org` FK, `last_used_at`, `revoked_at`. Custom auth class subclass updates `last_used_at` on each authenticated request.
- [AD-9] Graph API endpoint returns `{nodes, edges}` JSON in Cytoscape.js `data` wrapper format. Phase 6 also produces a Graphviz SVG stored in S3 for static download. No PyVis HTML generated or served.
- [AD-10] Always use `task.delay_on_commit()` (never `.delay()` or `.apply_async()` without `using=connection`) when dispatching from within a database transaction. `@shared_task` on all task definitions.
- [AD-11] Artifact downloads return `303 See Other` to a presigned S3/MinIO URL (24-hour TTL). Django never reads or streams artifact bytes.
- [AD-12] `SBOMJob.status` mutated only by Celery task code via a dedicated service function. The sole exception: `manifests/views.py` sets initial `status='PENDING'` before `delay_on_commit()`.
- [AD-13] Monorepo layout: `backend/` (Django + pixi) and `frontend/` (React + Vite + npm) are project-root peers. `manage.py`, `pixi.toml`, `pyproject.toml` under `backend/`. `docker-compose.yml`, `README.md`, `LICENSE` at project root.
- [Scaffold] Project scaffold uses `cookiecutter-django 2026.26.4` with Celery + Redis + PostgreSQL + S3 options selected. This is Epic 1 Story 1 — the scaffold is the first deliverable.
- [Naming] Module naming: Django apps `snake_case`; service functions `verb_noun(org, ...)`; selectors `get_noun_by_x(org, ...)`; tasks `verb_noun_task`.
- [File roles] `views.py` = DRF viewsets only; `services.py` = mutation logic; `selectors.py` = read-only queries; `models.py` = ORM only, no business logic.
- [API shape] All endpoints under `/api/v1/`; error envelope `{"error": "<message>", "code": "<snake_case_code>"}` ; dates ISO 8601 UTC; `task_id` is UUID v4.
- [Health check] `GET /health/` returns `{"status": "ok"}` with `200`; unauthenticated; used for Docker Compose `healthcheck:`.
- [Analysis chord] Each analysis task returns `{"report_type": "vuln|license|graph|version", "artifact_key": "<s3_key>|null", "summary": {...}, "failed": bool, "failure_reason": "<str>|null"}`.
- [Pagination] `PageNumberPagination`; default `page_size=25`, max 100 via `?page_size=`; envelope: `{"count": N, "next": "<url>|null", "previous": "<url>|null", "results": [...]}`.
- [Frontend data] All API calls from `frontend/src/api/`; no direct `fetch` calls in components; polling via shared `useJobStatus(taskId)` hook.
- [Storage paths] Manifests: `manifest-uploads/{org_id}/{upload_id}/{filename}`; Artifacts: `sbom-results/{org_id}/{task_id}/{filename}.{ext}`.
- [Artifact cleanup] `artifacts_expire_at` set at job creation (`completed_at + 10 days`); cleanup selector: `SBOMJob.objects.filter(artifacts_expire_at__lte=now(), result_key__isnull=False)`; after S3 deletion null `result_key` and `artifact_key` on related rows; job record never deleted.

### UX Design Requirements

No UX design contract exists for this project. Frontend implementation follows the React + MUI 9 + Cytoscape.js stack defined in the architecture spine.

### FR Coverage Map

```
FR-1.1–FR-1.7 → Epic 2 — Account, Org & API Key Management
FR-2.1–FR-2.6 → Epic 2 — Account, Org & API Key Management
FR-3.1–FR-3.7 → Epic 3 — Manifest Upload, Job Submission & SBOM Generation
FR-4.1–FR-4.7 → Epic 3 — Manifest Upload, Job Submission & SBOM Generation
FR-5.1–FR-5.5 → Epic 4 — Analysis Reports
FR-6.1–FR-6.8 → Epic 5 — SBOM Results Web UI
FR-7.1–FR-7.5 → Epic 6 — Job History Dashboard
FR-8.1–FR-8.5 → Epic 7 — Artifact Retention & Lifecycle Management
```

NFRs addressed per epic:
- Epic 1: NFR-5.1 (Docker Compose), NFR-5.2 (env config), NFR-5.3 (structlog), NFR-5.4 (Apache 2.0 license)
- Epic 2: NFR-1.1 (org isolation), NFR-1.2 (Redis key scoping), NFR-3.2 (artifact auth), NFR-3.3 (API key hashing), NFR-3.4 (upload validation)
- Epic 3: NFR-2.1 (pipeline performance), NFR-3.1 (safe loaders), NFR-4.1 (concurrency gate), NFR-6.1 (phase logging), NFR-6.2 (task failure logging)
- Epic 4: NFR-4.2 (rate limiting), NFR-6.1, NFR-6.2
- Epic 5: NFR-2.2 (UI load time)
- Epic 6: (no additional NFRs)
- Epic 7: (no additional NFRs)

## Epic List

### Epic 1: Project Foundation & Development Environment
Establishes the project scaffold, monorepo layout, Docker Compose stack, base Django configuration, core shared abstractions (`OrgScopedModel`, `OrgScopedQuerySet`, health check), CI pipeline, and structured logging. Delivers a reproducible, deployable development environment that all subsequent epics build on.
**FRs covered:** — (foundation only)
**NFRs addressed:** NFR-5.1, NFR-5.2, NFR-5.3, NFR-5.4
**Architecture:** AD-13 (monorepo layout), AD-2 (OrgScopedModel base class), AD-5 (SPA skeleton wired into Django static serving)

### Epic 2: Account, Org & API Key Management
Users can register, create orgs, manage team membership, and create/revoke API keys. Delivers the complete authentication and authorization layer — both the API surface and the React web UI (registration, login, org switcher, member management, API key UI).
**FRs covered:** FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.6, FR-1.7, FR-2.1, FR-2.2, FR-2.3, FR-2.4, FR-2.5, FR-2.6
**NFRs addressed:** NFR-1.1, NFR-1.2, NFR-3.2, NFR-3.3, NFR-3.4
**Architecture:** AD-2, AD-8

### Epic 3: Manifest Upload, Job Submission & SBOM Generation
Users can upload a Python dependency manifest, submit a SBOM generation job, and receive a generated SBOM document. Covers the full pipeline Phases 1–3 (detect & parse, resolve transitive dependencies, generate SBOM document) plus job submission, concurrency gating, status polling API, and timeout handling.
**FRs covered:** FR-3.1, FR-3.2, FR-3.3, FR-3.4, FR-3.5, FR-3.6, FR-3.7, FR-4.1, FR-4.2, FR-4.3, FR-4.4, FR-4.5, FR-4.6, FR-4.7
**NFRs addressed:** NFR-2.1, NFR-3.1, NFR-4.1, NFR-6.1, NFR-6.2
**Architecture:** AD-3, AD-4, AD-6, AD-7, AD-10, AD-11, AD-12

### Epic 4: Analysis Reports
The pipeline's parallel analysis phases (Phases 4–7) run and produce four reports: vulnerability findings (OSV + NVD CWE enrichment), license compliance (four-tier classification), dependency graph (`{nodes, edges}` JSON + Graphviz SVG), and version currency. Includes external API caching in Redis.
**FRs covered:** FR-5.1, FR-5.2, FR-5.3, FR-5.4, FR-5.5
**NFRs addressed:** NFR-4.2, NFR-6.1, NFR-6.2
**Architecture:** AD-4 (analysis queue), AD-6, AD-9, AD-11

### Epic 5: SBOM Results Web UI
Users can view complete SBOM results in the browser through a five-tab results page: Overview (summary stats + SBOM download), Vulnerabilities (sortable/filterable table), Licenses (four-tier grouped display), Dependency Graph (interactive Cytoscape.js with dagre layout + SVG download), and Version Currency (sortable table). Includes shareable results URL and failed-phase graceful degradation.
**FRs covered:** FR-6.1, FR-6.2, FR-6.3, FR-6.4, FR-6.5, FR-6.6, FR-6.7, FR-6.8
**NFRs addressed:** NFR-2.2
**Architecture:** AD-5, AD-9

### Epic 6: Job History Dashboard
Users can see all SBOM generation jobs for their org in a paginated dashboard with live progress updates, status filtering, and direct links to results. In-progress jobs show real-time phase and progress via 5-second polling.
**FRs covered:** FR-7.1, FR-7.2, FR-7.3, FR-7.4, FR-7.5
**Architecture:** AD-2, AD-5

### Epic 7: Artifact Retention & Lifecycle Management
Generated artifacts are automatically purged after 10 days via a scheduled Celery Beat job. Users can manually delete artifacts before expiry; org admins can bulk-delete. Expired artifacts are clearly indicated in the UI while job metadata remains visible.
**FRs covered:** FR-8.1, FR-8.2, FR-8.3, FR-8.4, FR-8.5
**Architecture:** AD-4, AD-6

---

## Epic 1: Project Foundation & Development Environment

Establishes the project scaffold, monorepo layout, Docker Compose stack, base Django configuration, core shared abstractions (`OrgScopedModel`, `OrgScopedQuerySet`, health check), CI pipeline, and React SPA wiring. Delivers a reproducible, deployable development environment that all subsequent epics build on.

### Story 1.1: Backend Scaffold & Developer Toolchain

As a developer,
I want a configured backend project scaffold with consistent tooling,
So that I can start implementing features immediately without setup decisions.

**Acceptance Criteria:**

**Given** a fresh clone of the repository,
**When** I `cd backend/` and run `pixi install`,
**Then** all dependencies install without error and the pixi environment is ready.

**Given** the `backend/` directory with the initial scaffold,
**When** I run `pixi run fmt && pixi run lint && pixi run check`,
**Then** all three pass on the initial scaffold with zero errors or warnings.

**Given** the `backend/` directory,
**When** I run `pixi run test`,
**Then** the pytest test suite runs and exits 0 (zero tests collected is acceptable at this stage).

**Given** the `backend/` directory,
**When** I run `pixi run ci`,
**Then** all five steps pass: pre-commit, build, mypy (strict), ruff, cov.

**Given** a git commit with a non-Conventional-Commits message (e.g., "updated stuff"),
**When** the commit-msg pre-commit hook runs,
**Then** the hook rejects the commit with an informative error.

**Given** the project root,
**When** I inspect the directory layout,
**Then** `manage.py`, `pixi.toml`, and `pyproject.toml` live under `backend/`; `docker-compose.yml`, `README.md`, and `LICENSE` (Apache 2.0) live at the project root; `frontend/` is a peer to `backend/` (AD-13).

**Given** `pyproject.toml` in `backend/`,
**When** ruff and mypy configurations are read,
**Then** ruff `line-length=120`, mypy `strict=true`, Google-style docstrings enforced, Python 3.10+ union syntax required.

**Given** `.github/workflows/ci.yml`,
**When** a push or PR is opened against `main`,
**Then** the `unit` job runs `pixi run test` and the `full` job runs `pixi run ci` across the Python matrix (3.12, 3.13, 3.14-dev).

---

### Story 1.2: Docker Compose Full Stack

As a developer,
I want to start the full application stack with a single command,
So that I can develop and test against real infrastructure locally.

**Acceptance Criteria:**

**Given** a `.env` file populated from `.env.example`,
**When** I run `docker compose up` from the project root,
**Then** all eight services start successfully: `web`, `worker-pipeline`, `worker-analysis`, `beat`, `postgres`, `redis`, `minio`, and `frontend-build`.

**Given** all services running,
**When** I send `GET /health/` with no authentication headers,
**Then** the response is `200 OK` with body `{"status": "ok"}`.

**Given** the Docker Compose `web` service healthcheck directive,
**When** Django is ready to serve requests,
**Then** Docker marks the `web` container healthy and dependent services start.

**Given** `docker-compose.yml`,
**When** I inspect the `build.context` for each service,
**Then** all Django services (`web`, `worker-pipeline`, `worker-analysis`, `beat`) use `./backend` and the `frontend-build` service uses `./frontend` (AD-13).

**Given** `docker-compose.yml`,
**When** I inspect the volumes section,
**Then** a `frontend-dist` named volume is declared; `frontend-build` mounts it at `/app/dist` (write); `web` mounts it read-only at `/app/frontend/dist`.

**Given** `docker-compose.yml`,
**When** I search for hardcoded secrets (passwords, keys, tokens),
**Then** none are found; all sensitive values reference environment variables.

**Given** `.env.example` committed to the repository,
**When** a developer copies it to `.env` and fills in the required values,
**Then** `docker compose up` completes without error and all services become healthy.

---

### Story 1.3: Core Shared Abstractions & Django Configuration

As a developer,
I want core Django configuration and shared base classes in place,
So that all feature apps can be built consistently on top of them without re-deciding foundational patterns.

**Acceptance Criteria:**

**Given** `OrgScopedModel` defined as an abstract Django model,
**When** any app's `models.py` extends it,
**Then** the concrete model automatically receives an `org` FK to `Org` and the `OrgScopedQuerySet` default manager with a `.for_org(org)` method — no migration is generated for the abstract base itself.

**Given** `OrgScopedQuerySet.for_org(org)`,
**When** called on any queryset derived from `OrgScopedModel`,
**Then** it returns only records where `org` matches the supplied org; records from other orgs are excluded.

**Given** `structlog` configured in `backend/config/settings/base.py`,
**When** any module calls `structlog.get_logger().info("event", key="value")`,
**Then** the log output is a single JSON line containing the event name and the key-value pair; no `print()` or stdlib `logging` calls appear anywhere in the codebase.

**Given** `django-environ` configured in `backend/config/settings/base.py`,
**When** `DATABASE_URL`, `REDIS_URL`, and `AWS_*` / MinIO vars are present in the environment,
**Then** Django connects to PostgreSQL, Celery connects to Redis, and `django-storages` connects to MinIO without any hardcoded values.

**Given** `backend/config/celery_app.py`,
**When** a Celery worker starts with `celery -A config.celery_app worker`,
**Then** it connects to the Redis broker and the app is discoverable; all future task modules decorated with `@shared_task` will be auto-discovered.

**Given** `backend/config/settings/` containing `base.py`, `local.py`, and `production.py`,
**When** `DJANGO_SETTINGS_MODULE` is set to `config.settings.local`,
**Then** Django starts without error, `DEBUG=True`, and uses the local database and Redis URLs.

**Given** unit tests covering `OrgScopedModel` and `OrgScopedQuerySet`,
**When** `pixi run cov` runs,
**Then** coverage on the affected modules is ≥90% and `pixi run ci` exits 0.

---

### Story 1.4: React SPA Foundation

As a developer,
I want a React SPA foundation wired into Django's static serving,
So that all frontend features can be built on a consistent stack and served correctly in both dev and production.

**Acceptance Criteria:**

**Given** the `frontend/` directory at the project root (AD-13),
**When** I run `npm install && npm run build` from `frontend/`,
**Then** `frontend/dist/` is populated with built assets (at minimum `index.html` and a JS bundle) and the command exits 0.

**Given** `collectstatic` has run in the `backend/` environment,
**When** I send `GET /` to the Django web server,
**Then** Django serves `frontend/dist/index.html` via WhiteNoise with a `200` response.

**Given** the React app loaded in a browser,
**When** I navigate to any path not handled by the Django URL router (e.g., `/dashboard`),
**Then** Django returns the SPA `index.html` (catch-all URL pattern) and React Router handles the route client-side — no Django 404.

**Given** `backend/config/settings/base.py`,
**When** I inspect `STATICFILES_DIRS`,
**Then** it contains `BASE_DIR.parent.parent / 'frontend' / 'dist'` (resolves to `frontend/dist/` relative to the project root, per AD-5).

**Given** `frontend/src/api/`,
**When** a developer needs to call a REST API endpoint,
**Then** the call is made via a function in `frontend/src/api/` — no direct `fetch` or `axios` calls appear in component files (AD-5).

**Given** `frontend/vite.config.ts`,
**When** `npm run build` executes,
**Then** the output directory is set to `../dist` (relative to `frontend/src`) resolving to `frontend/dist/` — matching what Django's `STATICFILES_DIRS` references.

**Given** `pixi run ci` run from `backend/`,
**When** the CI steps execute,
**Then** no npm or frontend build commands are invoked — frontend toolchain is independent (AD-13).

---

## Epic 2: Account, Org & API Key Management

Users can register, create orgs, manage team membership, and create/revoke API keys. Delivers the complete authentication and authorization layer — both the API surface and the React web UI. Web UI sessions use Django session auth (cookie-based); programmatic API access uses `Authorization: Api-Key <key>` — DRF is configured for both simultaneously.

### Story 2.1: User & Org Data Models + Registration

As a new user,
I want to register with my email and password,
So that I have an account with a personal org and can start submitting jobs.

**Acceptance Criteria:**

**Given** the registration page at `/register`,
**When** I submit a valid email and password,
**Then** a `User` account is created, a personal `Org` is created (name derived from the email prefix), and an `OrgMembership` with `role="admin"` links the two.

**Given** the registration form,
**When** I submit an email that is already registered,
**Then** I receive a validation error and no new account or org is created.

**Given** the `User`, `Org`, and `OrgMembership` models,
**When** I inspect `OrgMembership.role`,
**Then** it accepts only `"admin"` or `"member"` — enforced at the model and serializer level.

**Given** `OrgMembership` and `Org` extend `OrgScopedModel` (where applicable),
**When** `pixi run check` runs,
**Then** mypy (strict) passes on all three models with no errors.

**Given** unit tests covering the registration service function and all three models,
**When** `pixi run cov` runs,
**Then** coverage on `users/` models and the registration logic is ≥90%.

---

### Story 2.2: Login, Session Auth & Org Switcher

As a registered user,
I want to log in with my email and password and switch between my orgs,
So that I can access the resources of whichever org I'm currently working in.

**Acceptance Criteria:**

**Given** the login page at `/login`,
**When** I submit valid credentials,
**Then** a Django session is created and I am redirected to the dashboard.

**Given** the login page,
**When** I submit an invalid email or password,
**Then** I receive the message "Invalid email or password" with no hint about which field is wrong.

**Given** I am logged in and belong to multiple orgs,
**When** I open the org switcher in the navigation bar,
**Then** I see all orgs I belong to; the currently active org is visually indicated.

**Given** the org switcher,
**When** I select a different org,
**Then** the active org updates in the session and the dashboard reloads showing only that org's jobs and API keys (FR-1.6).

**Given** an unauthenticated browser request to any protected React route (e.g., `/dashboard`),
**When** the page loads,
**Then** the user is redirected to `/login`.

**Given** I am logged in and navigate to `/logout`,
**When** the action completes,
**Then** my session is invalidated and I am redirected to `/login`.

**Given** the DRF authentication configuration,
**When** a request carries a valid session cookie but no `Authorization: Api-Key` header,
**Then** the request authenticates via session auth and the active org is read from the session.

---

### Story 2.3: Org Administration & Membership Management

As an org admin,
I want to create orgs, add and remove members, transfer admin rights, and allow users to leave orgs,
So that I can manage my team's access to the service.

**Acceptance Criteria:**

**Given** I am logged in,
**When** I submit the create-org form with a unique name,
**Then** a new `Org` is created and I am added as its admin via a new `OrgMembership` (FR-1.2).

**Given** I am an org admin,
**When** I submit the add-member form with a new member's email and temporary password,
**Then** a `User` account is created (or the existing user is found) and an `OrgMembership` with `role="member"` is created; no email is sent (FR-1.3).

**Given** I am an org admin and call `DELETE /api/v1/orgs/{org_id}/members/{user_id}/`,
**When** the request is processed,
**Then** the user's `OrgMembership` is deleted immediately and they can no longer access any resource in that org (FR-1.4).

**Given** I am an org admin and transfer admin privileges to another member via the UI,
**When** the transfer completes,
**Then** the target member's role is set to `"admin"`; my role is set to `"member"` if I was the only admin (FR-1.5).

**Given** an org with exactly one admin,
**When** that admin attempts to remove themselves, leave the org, or transfer away admin without a replacement,
**Then** the action is rejected with error `"An org must always have at least one admin."`.

**Given** I am a non-sole-admin member of an org,
**When** I select "Leave org" in the UI,
**Then** my `OrgMembership` is deleted and the org no longer appears in my org switcher (FR-1.7).

**Given** `GET /api/v1/orgs/{org_id}/members/` with a valid API key scoped to that org,
**When** the request is processed,
**Then** the response lists all members with name, email, role, and joined date; members from other orgs are not included (AD-2).

**Given** a member (non-admin) views the membership management page,
**When** the page renders,
**Then** the add-member form, remove buttons, and transfer-admin controls are not rendered.

---

### Story 2.4: API Key Management

As an org admin,
I want to create, list, and revoke API keys for my org,
So that developers and CI pipelines can authenticate against the REST API programmatically.

**Acceptance Criteria:**

**Given** I am an org admin and call `POST /api/v1/keys/` with a `name`,
**When** the key is created,
**Then** the response includes the full plaintext key value exactly once; subsequent `GET /api/v1/keys/` shows only the first 8-character prefix plus a masked suffix — the plaintext key is never retrievable again (FR-2.1, AD-8).

**Given** an org already has 10 active (non-revoked) API keys,
**When** I attempt to create an 11th via `POST /api/v1/keys/`,
**Then** the response is `400` with `{"error": "This org has reached the maximum of 10 active API keys.", "code": "api_key_limit_reached"}` (FR-2.2).

**Given** I am an org admin and call `DELETE /api/v1/keys/{key_id}/`,
**When** the request is processed,
**Then** `OrgApiKey.revoked_at` is set to the current timestamp immediately; any subsequent request using that key returns `401` (FR-2.3).

**Given** `GET /api/v1/keys/` with a valid session or API key scoped to the org,
**When** the request is processed,
**Then** the response lists all active (non-revoked) keys with `name`, `prefix`, `created_at`, and `last_used_at` (FR-2.4).

**Given** a DRF request with header `Authorization: Api-Key <valid-key>`,
**When** the custom auth class processes the request,
**Then** the request is authenticated, `request.auth` is the `OrgApiKey` instance, `request.auth.org` is the key's org, and `last_used_at` is updated to now (AD-8).

**Given** a DRF request with a revoked or non-existent key in the `Authorization: Api-Key` header,
**When** the request is processed,
**Then** the response is `401` with `{"error": "Invalid or revoked API key.", "code": "invalid_api_key"}` (FR-2.5).

**Given** an API request where the authenticated key belongs to Org A and targets a resource owned by Org B,
**When** the request is processed,
**Then** the response is `404` — existence of the resource is not disclosed to the requesting org (AD-2, FR-2.6).

**Given** the web UI API key management page viewed by an admin,
**When** the page renders,
**Then** a table shows all active keys (name, prefix, created date, last used date) and a "Create key" button is present; the full plaintext key is displayed in a dismissible modal only immediately after creation.

**Given** the web UI API key management page viewed by a non-admin member,
**When** the page renders,
**Then** the "Create key" button and "Revoke" controls are absent.

---

## Epic 3: Manifest Upload, Job Submission & SBOM Generation

Users can upload a Python dependency manifest, submit a SBOM generation job, and receive a generated SBOM document. Covers the full pipeline Phases 1–3 (detect & parse, resolve transitive dependencies, generate SBOM document) plus Phase 8 (persist), job submission, concurrency gating, status polling API, and timeout handling. Phases 4–7 (analysis) are stubbed as a no-op group here and filled in by Epic 4.

### Story 3.1: Manifest Upload & Format Detection

As a user,
I want to upload a Python manifest file that is validated and its format detected,
So that I can be confident the file will be processed correctly before a job is queued.

**Acceptance Criteria:**

**Given** the `ManifestUpload` model and a valid `requirements.txt` under 50 MB,
**When** it is uploaded via `POST /api/v1/sbom/generate/` or the web UI,
**Then** the file is stored at `manifest-uploads/{org_id}/{upload_id}/{filename}`, a `ManifestUpload` record is created scoped to the org, and `detected_format` is set to `requirements` (FR-3.1).

**Given** a file whose name and structural markers match one of the five supported formats,
**When** format detection runs,
**Then** the detection heuristic is applied in order: `pixi.lock` → `pixi.toml` → `pyproject.toml` (+`[tool.poetry]` note) → PEP 621 `pyproject.toml` → `environment.yml`/`.yaml` → `requirements*.txt` (FR-3.3).

**Given** an uploaded file with an unsupported extension (e.g., `Pipfile`),
**When** validation runs,
**Then** the response is `400` with `{"error": "Unsupported manifest format. Supported: requirements.txt, pyproject.toml, pixi.lock, pixi.toml, environment.yml", "code": "unsupported_format"}` and no `ManifestUpload` or job is created (FR-3.2).

**Given** detection is ambiguous,
**When** the request includes an optional `manifest_format` parameter,
**Then** the supplied format overrides automatic detection (FR-3.3).

**Given** a file exceeding 50 MB,
**When** it is uploaded,
**Then** the response is `400` with a size-limit error before any storage write (FR-3.4).

**Given** any uploaded manifest,
**When** its content is parsed during validation,
**Then** only safe loaders are used (`tomllib`, PyYAML safe load, `packaging`); no content reaches `eval`, `exec`, or a shell (FR-3.4, NFR-3.1).

**Given** a file that passes MIME and size checks but fails safe-parse (malformed content),
**When** validation runs,
**Then** the response is `400` with a parse-error message and no task is enqueued (FR-3.4).

**Given** an upload attempting path traversal in the filename (e.g., `../../etc/passwd`),
**When** the file is stored,
**Then** the filename is sanitized and the stored path stays within `manifest-uploads/{org_id}/{upload_id}/` (NFR-3.4).

---

### Story 3.2: Job Submission, Concurrency Gate & Status API

As a user,
I want to submit a validated manifest and immediately receive a task ID I can poll,
So that I get a fast response and can track progress asynchronously.

**Acceptance Criteria:**

**Given** a validated manifest and an org below its concurrency limit,
**When** I `POST /api/v1/sbom/generate/` with an optional `output_format`,
**Then** a `SBOMJob` is created with `status="PENDING"`, `artifacts_expire_at` is left null until completion, the pipeline task is dispatched via `delay_on_commit()`, and the response is `202` with `{task_id, status_url, estimated_seconds}` (FR-3.5, AD-10, AD-12).

**Given** the `output_format` parameter,
**When** it is `cdx-json` (default), `cdx-xml`, or `spdx-2.3`,
**Then** the value is accepted and stored on the job; any other value returns `400` with a clear error (FR-3.6).

**Given** the submitting org already has `SBOM_MAX_CONCURRENT_JOBS_PER_ORG` jobs in `PENDING` or `PROGRESS`,
**When** I submit another job,
**Then** the concurrency gate in `manifests/views.py` returns `429` with a `Retry-After` header and no job is created (FR-3.5, AD-7, NFR-4.1).

**Given** the concurrency count check,
**When** it executes,
**Then** it uses `SBOMJob.objects.for_org(org).filter(status__in=['PENDING', 'PROGRESS']).count()` before dispatch (AD-7).

**Given** a job owned by Org A,
**When** the same user acting under Org B calls `GET /api/v1/sbom/status/{task_id}/`,
**Then** the response is `404` — the job is invisible outside its owning org (FR-3.7, AD-2).

**Given** an active job,
**When** I `GET /api/v1/sbom/status/{task_id}/`,
**Then** the response includes `status` (`PENDING`/`PROGRESS`/`SUCCESS`/`FAILURE`), `progress` (0–100), `current_phase` name, and — on success — a `result_url` (FR-4.7).

**Given** the `estimated_seconds` value,
**When** a job is submitted,
**Then** it is computed from manifest format and file size and returned in the `202` response (FR-3.5).

**Given** `SBOMJob.status`,
**When** any code other than the initial `PENDING` set in `manifests/views.py` attempts to write it from a view,
**Then** that is a violation — status is mutated only by Celery task code via a dedicated `sbom/services.py` function (AD-12).

---

### Story 3.3: Manifest Parsers & Transitive Resolution (Phases 1–2)

As the SBOM pipeline,
I want to parse each supported manifest format and resolve its full transitive dependency tree,
So that a complete resolved package list is available for SBOM generation.

**Acceptance Criteria:**

**Given** a `pixi.lock` file,
**When** Phase 2 runs,
**Then** it is parsed with PyYAML safe load (not `tomllib`) and the full transitive tree is read directly from the lock file with no external resolver invoked (FR-4.3).

**Given** a `pixi.toml`, `pyproject.toml` (no lock), or `requirements.txt`,
**When** Phase 2 runs,
**Then** the manifest is parsed with the correct loader (`tomllib` / `packaging.requirements.Requirement`) and `uv pip compile` is invoked as a subprocess to resolve the transitive tree (FR-4.3).

**Given** a `conda environment.yml`,
**When** Phase 2 runs,
**Then** it is parsed with PyYAML safe load and the `conda`/`mamba` solver is invoked; if the solver binary is unavailable the phase fails with a descriptive error naming the missing solver (FR-4.3).

**Given** each parser lives in `sbom/parsers/`,
**When** a parser is implemented,
**Then** it is a pure service-layer function taking plain inputs and returning a resolved package list (name, version, dependencies) — no `HttpRequest`, `Response`, or Celery `Task` coupling (AD-3).

**Given** Phase 1 (detect & parse) and Phase 2 (resolve),
**When** each phase starts,
**Then** `task.update_state(state='PROGRESS', meta={'progress': N, 'current_step': '<phase name>'})` is called with thresholds in the 0–15% (Phase 1) and 15–40% (Phase 2) ranges (FR-4.2).

**Given** each pipeline phase,
**When** it starts and completes,
**Then** a structured `structlog` entry is emitted with phase name, duration, and package count, binding `org_id` and `task_id` (NFR-6.1).

**Given** unit tests with representative fixture files for all five formats,
**When** `pixi run cov` runs,
**Then** each parser is exercised and coverage on `sbom/parsers/` is ≥90%.

---

### Story 3.4: SBOM Document Generation & Persistence (Phases 3 & 8)

As the SBOM pipeline,
I want to generate a standards-compliant SBOM document from the resolved package list and persist it,
So that the user can download their SBOM in the requested format.

**Acceptance Criteria:**

**Given** a resolved package list and `output_format="cdx-json"` or `"cdx-xml"`,
**When** Phase 3 runs,
**Then** a CycloneDX 1.6 document is generated using `cyclonedx-python-lib` in the requested serialization (FR-4.4).

**Given** a resolved package list and `output_format="spdx-2.3"`,
**When** Phase 3 runs,
**Then** an SPDX 2.3 JSON document is generated using `lib4sbom` (FR-4.4).

**Given** the resolved package list is the shared input,
**When** Phase 3 selects a serializer,
**Then** the same resolved list feeds either library — format selection alone determines the serializer (FR-4.4).

**Given** Phase 3 fails (e.g., serializer error),
**When** the failure is caught,
**Then** the job is marked `FAILED` entirely and no partial SBOM is produced (FR-4.5).

**Given** a successfully generated SBOM,
**When** Phase 8 (persist) runs,
**Then** the document is written to `sbom-results/{org_id}/{task_id}/{filename}.{ext}` in S3/MinIO, `SBOMJob.result_key` is set, `artifacts_expire_at` is set to `completed_at + 10 days`, and `summary_stats` (total package count) is populated (FR-4.2, AD-6).

**Given** the SBOM artifact key stored in PostgreSQL,
**When** a client calls `GET /api/v1/sbom/result/{task_id}/`,
**Then** the response is `303 See Other` redirecting to a presigned S3/MinIO URL (24-hour TTL); Django never streams artifact bytes (FR-4.7, AD-11).

**Given** Phases 3 and 8 route to the `pipeline` queue,
**When** the tasks are enqueued,
**Then** they run on the `pipeline` worker, never the `analysis` worker (AD-4).

**Given** blob storage,
**When** the SBOM is persisted,
**Then** only the artifact key (not the blob) is written to PostgreSQL; the blob lives only in S3/MinIO (AD-6).

---

### Story 3.5: Pipeline Orchestration, Progress & Timeout Handling

As the SBOM pipeline,
I want an orchestrated eight-phase Celery chain with progress reporting and timeout handling,
So that jobs run end-to-end reliably and failures are surfaced cleanly to the user.

**Acceptance Criteria:**

**Given** a dispatched job,
**When** the pipeline runs,
**Then** it executes as a Celery chain: Phase 1 → 2 → 3 → (parallel group of Phases 4–7, stubbed as a no-op group in this epic) → chord callback → Phase 8, with Phases 1–3 and 8 on the `pipeline` queue (FR-4.1, FR-4.2, AD-4).

**Given** the analysis group is stubbed in this epic,
**When** the chord callback runs,
**Then** it aggregates an empty analysis result and proceeds to Phase 8 — Epic 4 replaces the stub with the four real analysis tasks without changing the orchestration shape.

**Given** each phase boundary,
**When** a phase begins,
**Then** progress is reported via `task.update_state()` matching the thresholds in FR-4.2 (0–15, 15–40, 40–55, 55–80, 80–88, 88–93, 93–97, 97–100), so a polling client sees monotonically increasing progress (FR-4.1).

**Given** a job exceeds the 25-minute soft limit,
**When** `SoftTimeLimitExceeded` is raised,
**Then** the task catches it, marks the job `FAILED` with reason `"soft_timeout"`, releases held resources, and returns no partial SBOM (FR-4.6).

**Given** a job exceeds the 30-minute hard limit and the worker is force-terminated,
**When** the next status poll or cleanup sweep runs,
**Then** the job is marked `FAILED` with reason `"hard_timeout"` (FR-4.6).

**Given** either timeout reason is set,
**When** the user views job status,
**Then** the failure reason (`soft_timeout` / `hard_timeout`) is surfaced in the status response (FR-4.6).

**Given** a Celery task failure at any phase,
**When** the failure is logged,
**Then** the log entry includes the full traceback and the manifest format that triggered it (NFR-6.2).

**Given** all task definitions,
**When** they are declared,
**Then** each uses `@shared_task` with no direct Celery app import in the task module (AD-10).

**Given** a manifest of <50 packages on a single 4-core worker,
**When** the full pipeline runs,
**Then** it completes within the NFR-2.1 target (under 35 seconds).

---

## Epic 4: Analysis Reports

The pipeline's parallel analysis phases (Phases 4–7) run and produce four reports: vulnerability findings (OSV + NVD CWE enrichment), license compliance (four-tier classification), dependency graph (`{nodes, edges}` JSON + Graphviz SVG), and version currency. Includes external API caching in Redis. Replaces the Epic 3 no-op analysis stub.

### Story 4.1: External API Caching, Rate Limiting & AnalysisReport Model

As the analysis subsystem,
I want shared caching, rate limiting, and a report persistence model,
So that all four analysis phases reuse consistent infrastructure and respect external API limits.

**Acceptance Criteria:**

**Given** the `AnalysisReport` model,
**When** it is created,
**Then** it has a FK to `SBOMJob`, a `report_type` field (`vuln`/`license`/`graph`/`version`), `artifact_key`, `generated_at`, `failed` (bool), and `failure_reason` (nullable) — and is org-scoped through its parent job (AD-6).

**Given** `requests-cache` configured with a Redis backend,
**When** a PyPI JSON API response is fetched,
**Then** it is cached with a 1-hour TTL; an OSV API response is cached with a 24-hour TTL; cache keys are scoped by package name + version (FR-5.5).

**Given** the same package+version is requested by two different orgs,
**When** the second request hits the cache,
**Then** the cached public vulnerability/version data is served — the cache is safely shared across orgs (FR-5.5).

**Given** `requests-ratelimiter` configured for external calls,
**When** analysis tasks call external APIs,
**Then** OSV is limited to 1 req/s and PyPI JSON to 5 req/s (NFR-4.2).

**Given** all four analysis phases route to the `analysis` queue,
**When** their tasks are enqueued,
**Then** they run on the `analysis` worker, never the `pipeline` worker (AD-4).

**Given** the analysis service functions,
**When** they are implemented in `analysis/services/`,
**Then** each is a pure service-layer function returning plain Python objects — no HTTP or Celery coupling (AD-3).

**Given** unit tests using `respx` (or equivalent) to intercept external HTTP,
**When** `pixi run cov` runs,
**Then** caching, rate-limiting wiring, and the `AnalysisReport` model are covered ≥90% with no real network calls in unit tests.

---

### Story 4.2: Vulnerability Report — Phase 4

As a user,
I want a vulnerability report for my dependencies,
So that I know which packages have known CVEs and how severe they are.

**Acceptance Criteria:**

**Given** a resolved package list,
**When** Phase 4 runs,
**Then** it queries the OSV batch API (`POST https://api.osv.dev/v1/querybatch`) with all packages in batched requests (FR-5.1).

**Given** OSV returns findings for a package,
**When** the report is built,
**Then** each vulnerable package entry includes CVE/GHSA identifier(s), CVSS score and severity (Critical/High/Medium/Low) where available, and a link to the OSV advisory (FR-5.1).

**Given** OSV lacks CWE data for a finding,
**When** the report is enriched,
**Then** CWE classification is fetched from NVD and added to the entry (FR-5.1).

**Given** a package with no known vulnerabilities,
**When** the report is built,
**Then** that package is not listed in the vulnerability report (FR-5.1).

**Given** Phase 4 completes,
**When** the result is persisted,
**Then** an `AnalysisReport` with `report_type="vuln"` is created, its `artifact_key` points to the stored report JSON in S3/MinIO, and its `summary` records the vulnerable-package count (AD-6).

**Given** `GET /api/v1/sbom/result/{task_id}/reports/vulnerabilities/`,
**When** called with an org-scoped credential,
**Then** the vulnerability report JSON is returned (or `303` to a presigned URL per AD-11); a cross-org request returns `404` (AD-2).

**Given** Phase 4 starts and completes,
**When** each boundary is crossed,
**Then** progress updates cover the 55–80% range and a structured log entry records phase name, duration, and package count (FR-4.2, NFR-6.1).

---

### Story 4.3: License Compliance Report — Phase 5

As a user,
I want a license compliance report grouped by legal risk,
So that I can quickly see which dependencies need legal attention.

**Acceptance Criteria:**

**Given** a resolved package list,
**When** Phase 5 runs,
**Then** the declared license for each package is extracted from PyPI metadata (FR-5.2).

**Given** each package's license identifier,
**When** it is classified,
**Then** it is placed in exactly one of four tiers: Strong Copyleft (AGPL-3.0-only, GPL-2.0/3.0 families), Weak Copyleft (LGPL-2.1/3.0 families), Unknown (no license or non-SPDX identifier), or Permissive (all other SPDX identifiers) (FR-5.2).

**Given** the four tiers,
**When** the report is assembled,
**Then** tiers are ordered by descending attention required: Strong Copyleft → Weak Copyleft → Unknown → Permissive (FR-5.2).

**Given** a package with no declared license or a non-SPDX identifier,
**When** it is classified,
**Then** it is placed in the Unknown tier (FR-5.2).

**Given** Phase 5 completes,
**When** the result is persisted,
**Then** an `AnalysisReport` with `report_type="license"` is created with `artifact_key` and a `summary` recording per-tier counts (AD-6).

**Given** `GET /api/v1/sbom/result/{task_id}/reports/licenses/`,
**When** called with an org-scoped credential,
**Then** the license report JSON is returned; a cross-org request returns `404` (AD-2, AD-11).

**Given** Phase 5 starts and completes,
**When** each boundary is crossed,
**Then** progress updates cover the 80–88% range with structured logging (FR-4.2, NFR-6.1).

---

### Story 4.4: Dependency Graph — Phase 6

As a user,
I want a dependency graph in both interactive and downloadable forms,
So that I can explore my dependency tree visually and export a static copy.

**Acceptance Criteria:**

**Given** a resolved package list with `depends-on` relationships,
**When** Phase 6 runs,
**Then** a directed acyclic graph (DAG) is built using NetworkX (FR-5.3).

**Given** the built DAG,
**When** the graph JSON is produced,
**Then** it matches the exact Cytoscape.js shape: `{"nodes": [{"data": {"id": "<name>==<version>", "label": "<name>", "version": "<version>"}}], "edges": [{"data": {"source": "<node_id>", "target": "<node_id>"}}]}` (FR-5.3, AD-9).

**Given** the built DAG,
**When** the static artifact is produced,
**Then** a Graphviz SVG is rendered and stored in S3/MinIO for download (FR-5.3, AD-9).

**Given** `GET /api/v1/sbom/result/{task_id}/reports/graph/`,
**When** called with an org-scoped credential,
**Then** the `{nodes, edges}` JSON is returned; no PyVis HTML is ever generated or served (AD-9).

**Given** the Graphviz SVG,
**When** the client requests the downloadable graph,
**Then** it is served as a separate download via a presigned URL (AD-11).

**Given** Phase 6 completes,
**When** the result is persisted,
**Then** an `AnalysisReport` with `report_type="graph"` is created with `artifact_key` (the SVG) and a `summary` recording node and edge counts (AD-6).

**Given** Phase 6 starts and completes,
**When** each boundary is crossed,
**Then** progress updates cover the 88–93% range with structured logging (FR-4.2, NFR-6.1).

---

### Story 4.5: Version Currency Report — Phase 7

As a user,
I want a version currency report,
So that I can see which dependencies are outdated and by how much.

**Acceptance Criteria:**

**Given** a resolved package list,
**When** Phase 7 runs,
**Then** the latest stable version of each package is fetched from the PyPI JSON API (FR-5.4).

**Given** an installed version and the latest version,
**When** currency is classified,
**Then** it is one of: `current` (same release series), `behind-1` (one series behind), `behind-2+` (two or more series behind, including major-version gaps), or `unknown` (version data unavailable) (FR-5.4).

**Given** a package tracked in the LTS registry (Django, Python, plus any operator additions),
**When** its currency is classified,
**Then** LTS-aware classification is applied using the known LTS version (FR-5.4).

**Given** the `SBOM_LTS_REGISTRY` environment variable containing a JSON mapping of package name to LTS version string,
**When** the service loads the registry,
**Then** operator-supplied entries extend or override the built-in defaults (FR-5.4).

**Given** Phase 7 completes,
**When** the result is persisted,
**Then** an `AnalysisReport` with `report_type="version"` is created with `artifact_key` and a `summary` recording counts per currency class (AD-6).

**Given** `GET /api/v1/sbom/result/{task_id}/reports/versions/`,
**When** called with an org-scoped credential,
**Then** the version currency report JSON is returned; a cross-org request returns `404` (AD-2, AD-11).

**Given** Phase 7 starts and completes,
**When** each boundary is crossed,
**Then** progress updates cover the 93–97% range with structured logging (FR-4.2, NFR-6.1).

---

### Story 4.6: Analysis Group Integration & Partial-Failure Handling

As the SBOM pipeline,
I want the four analysis phases wired into the parallel group with graceful partial-failure handling,
So that a failed analysis never loses the SBOM and users see exactly what's unavailable.

**Acceptance Criteria:**

**Given** the Epic 3 no-op analysis stub,
**When** this story completes,
**Then** the stub is replaced by a real Celery group of the four analysis tasks (Phases 4–7) running in parallel on the `analysis` queue, joined by a chord callback (FR-4.2, AD-4).

**Given** each analysis task,
**When** it returns to the chord callback,
**Then** it returns the standard envelope `{"report_type": "vuln|license|graph|version", "artifact_key": "<s3_key>|null", "summary": {...}, "failed": bool, "failure_reason": "<str>|null"}` (AD-4 / conventions).

**Given** the chord callback receives the four envelopes,
**When** it runs,
**Then** it sets `AnalysisReport.failed` and `artifact_key` for each report from the envelope fields, then proceeds to Phase 8 (persist) on the `pipeline` queue.

**Given** one or more of Phases 4–7 fail,
**When** the job finishes,
**Then** the job still completes with a downloadable SBOM; the failed report(s) have `failed=True` and a `failure_reason`, while successful reports remain available (FR-4.5).

**Given** all four analysis phases succeed,
**When** the job finishes,
**Then** all four `AnalysisReport` rows have `failed=False` and valid `artifact_key`s.

**Given** an analysis report endpoint for a failed phase,
**When** it is requested,
**Then** the response conveys the failure with its `failure_reason` rather than returning stale or missing data (FR-4.5).

**Given** the full pipeline with real analysis phases,
**When** it runs against manifests of varying sizes,
**Then** completion times stay within the NFR-2.1 targets and `pixi run ci` exits 0 with ≥90% coverage on the analysis modules.

---

## Epic 5: SBOM Results Web UI

Users can view complete SBOM results in the browser through a five-tab results page: Overview, Vulnerabilities, Licenses, Dependency Graph, and Version Currency. Includes a stable shareable results URL, per-tab failed-phase graceful degradation, and the interactive Cytoscape.js graph. All data flows through the versioned REST API (AD-5).

### Story 5.1: Results Page Shell, Tab Navigation & Access Control

As a user,
I want a results page with five tabs that only my org can access,
So that I can navigate a completed job's outputs and safely share the URL within my team.

**Acceptance Criteria:**

**Given** a completed job owned by my org,
**When** I open its results page,
**Then** five tabs are rendered — Overview, Vulnerabilities, Licenses, Dependency Graph, Version Currency — with Overview active by default (FR-6.1).

**Given** the results page URL,
**When** another member of the same org opens it,
**Then** they see the same results (the URL is stable and shareable within the org) (FR-6.8).

**Given** a user who is not a member of the owning org,
**When** they open the results page URL,
**Then** the web UI route returns `403` (FR-6.8, AD-2).

**Given** any tab whose backing analysis phase failed (per FR-4.5),
**When** that tab is opened,
**Then** it displays a failure notice with the error reason instead of report content, while the SBOM download and successful tabs remain available (FR-6.7).

**Given** all API calls made by the results page,
**When** they are issued,
**Then** they go through functions in `frontend/src/api/` — no direct `fetch` calls in components (AD-5).

**Given** a job whose artifacts are still available,
**When** the results page loads (excluding graph rendering),
**Then** it renders in under 3 seconds (NFR-2.2).

---

### Story 5.2: Overview Tab

As a user,
I want an overview of my SBOM results with a download button,
So that I can grasp the summary at a glance and retrieve the SBOM.

**Acceptance Criteria:**

**Given** a completed job,
**When** I view the Overview tab,
**Then** it shows total package count, vulnerable package count, license category breakdown (permissive / copyleft / unknown), and package counts at current / behind / unknown versions (FR-6.2).

**Given** the Overview tab,
**When** I click the SBOM download button,
**Then** the SBOM artifact downloads in the format submitted at job creation, via the `303`-to-presigned-URL flow (FR-6.2, AD-11).

**Given** the Overview summary cards,
**When** I click a category (e.g., vulnerable packages),
**Then** I am linked to the corresponding analysis tab (FR-6.2).

**Given** an Overview summary metric backed by a failed analysis phase,
**When** the tab renders,
**Then** that metric indicates the data is unavailable rather than showing a misleading zero (FR-6.7).

---

### Story 5.3: Vulnerabilities Tab

As a user,
I want a sortable, filterable table of vulnerable packages,
So that I can prioritize which dependencies to address.

**Acceptance Criteria:**

**Given** a job with vulnerability findings,
**When** I view the Vulnerabilities tab,
**Then** a table lists package name, installed version, CVE/GHSA IDs, CVSS score, severity (Critical/High/Medium/Low), and an advisory link (FR-6.3).

**Given** the vulnerabilities table,
**When** I click a column header,
**Then** the table sorts by that column; severity sorts by rank (Critical highest) (FR-6.3).

**Given** the vulnerabilities table,
**When** I apply a severity filter,
**Then** only rows matching the selected severity are shown (FR-6.3).

**Given** a job with zero vulnerabilities,
**When** I view the tab,
**Then** it explicitly displays "No vulnerabilities found in X packages" rather than an empty table (FR-6.3).

**Given** the vulnerability phase failed,
**When** I view the tab,
**Then** a failure notice with the reason is shown (FR-6.7).

---

### Story 5.4: Licenses Tab

As a user,
I want packages grouped by license risk tier,
So that I can focus on the licenses that need legal attention.

**Acceptance Criteria:**

**Given** a job with license data,
**When** I view the Licenses tab,
**Then** packages are grouped into four tiers displayed in order: Strong Copyleft (Attention Required), Weak Copyleft (Review Recommended), Unknown, Permissive (FR-6.4).

**Given** each package row,
**When** it renders,
**Then** the package name links to its PyPI page (FR-6.4).

**Given** a tier with zero packages,
**When** the tab renders,
**Then** that tier is collapsed by default (FR-6.4).

**Given** the license phase failed,
**When** I view the tab,
**Then** a failure notice with the reason is shown (FR-6.7).

---

### Story 5.5: Dependency Graph Tab

As a user,
I want an interactive dependency graph with a download option,
So that I can explore my dependency tree and export a static copy.

**Acceptance Criteria:**

**Given** a job with graph data,
**When** I view the Dependency Graph tab,
**Then** the graph renders inline using Cytoscape.js with a hierarchical dagre layout, consuming the `{nodes, edges}` JSON from the graph endpoint (FR-6.5, AD-9).

**Given** the rendered graph,
**When** I interact with it,
**Then** zoom, pan, node drag, and hover-to-highlight all work (FR-6.5).

**Given** the Dependency Graph tab,
**When** I click "Download SVG",
**Then** the static Graphviz SVG artifact downloads (via presigned URL) (FR-6.5, AD-11).

**Given** the graph tab uses Cytoscape.js,
**When** it renders,
**Then** no PyVis HTML or iframe is used (AD-9).

**Given** the graph phase failed,
**When** I view the tab,
**Then** a failure notice with the reason is shown (FR-6.7).

---

### Story 5.6: Version Currency Tab

As a user,
I want a sortable table of package version currency,
So that I can see which dependencies are outdated and by how much.

**Acceptance Criteria:**

**Given** a job with version currency data,
**When** I view the Version Currency tab,
**Then** a table lists all packages with installed version, latest version, and a currency status badge (Current / Behind / Unknown) (FR-6.6).

**Given** the version currency table,
**When** it first loads,
**Then** packages classified `behind-2+` are displayed first by default (FR-6.6).

**Given** the version currency table,
**When** I sort by status,
**Then** rows reorder by currency status (FR-6.6).

**Given** the version currency phase failed,
**When** I view the tab,
**Then** a failure notice with the reason is shown (FR-6.7).

### Story 5.7: Light/Dark Theme Toggle (app-wide)

As a user,
I want to switch the interface between light and dark themes,
So that I can read the UI comfortably.

Added 2026-07-03 (Kevin): the SPA has no MUI ThemeProvider, so the UI is stuck on a hard-to-read default. App-wide; can be pulled forward ahead of the rest of Epic 5 since it affects pages already built in Epics 2–3.

**Acceptance Criteria:**

**Given** the app loads with no stored preference,
**When** it renders,
**Then** it follows the OS `prefers-color-scheme` via a MUI `ThemeProvider` + `CssBaseline`, and all fields/text are legible in both modes.

**Given** a theme toggle in the app chrome,
**When** I switch light↔dark,
**Then** the whole UI updates immediately and my choice persists (localStorage) across reloads with no wrong-theme flash on load.

---

## Epic 6: Job History Dashboard

Users can see all SBOM generation jobs for their active org in a paginated dashboard with live progress updates, status filtering, and direct links to results.

### Story 6.1: Jobs List API & Dashboard Table

As a user,
I want a dashboard listing all my org's SBOM jobs,
So that I can review past and current jobs and jump to their results.

**Acceptance Criteria:**

**Given** `GET /api/v1/jobs/` with an org-scoped credential,
**When** the request is processed,
**Then** it returns the org's jobs most-recent-first, each with submitted time, manifest filename, manifest format, output format, and status; jobs from other orgs are excluded (FR-7.1, AD-2).

**Given** the jobs list endpoint,
**When** results are returned,
**Then** they are paginated at 25 per page using the standard envelope `{"count", "next", "previous", "results"}` (FR-7.5).

**Given** the jobs list endpoint,
**When** I pass a status filter (`All`/`In Progress`/`Completed`/`Failed`) and/or a manifest-format filter,
**Then** only matching jobs are returned (FR-7.4).

**Given** the dashboard table in the web UI,
**When** it renders,
**Then** it shows columns for submitted time, manifest filename, manifest format, output format, status (with a visual indicator), and a link to results (FR-7.1).

**Given** a job in `FAILED` state,
**When** it appears in the list,
**Then** its row displays a failure reason summary (FR-7.3).

**Given** the dashboard filter controls,
**When** I select a status or manifest-format filter,
**Then** the table updates to show only matching jobs, driven by the API filter parameters (FR-7.4).

**Given** a completed job row,
**When** I click its results link,
**Then** I navigate to that job's five-tab results page (FR-7.1).

---

### Story 6.2: Live Progress Polling

As a user,
I want in-progress jobs to update their progress automatically,
So that I can watch a job advance without manually refreshing.

**Acceptance Criteria:**

**Given** a job in `PENDING` or `PROGRESS` state on the dashboard,
**When** the dashboard is open,
**Then** its progress percentage and current phase name are polled from `GET /api/v1/sbom/status/{task_id}/` every 5 seconds and updated in place (FR-7.2).

**Given** the polling implementation,
**When** a component needs job status,
**Then** it uses the shared `useJobStatus(taskId)` hook — no bespoke polling logic per component (AD-5 conventions).

**Given** a job that transitions to `SUCCESS` or `FAILURE` while being polled,
**When** the terminal state is received,
**Then** polling for that job stops and the row updates to its final state (with results link on success, failure reason on failure) (FR-7.2, FR-7.3).

**Given** no WebSocket infrastructure exists,
**When** live updates occur,
**Then** they are achieved purely through the 5-second HTTP polling (FR-7.2).

**Given** the dashboard has no in-progress jobs,
**When** it is open,
**Then** no status polling requests are issued.

---

## Epic 7: Artifact Retention & Lifecycle Management

Generated artifacts are automatically purged after 10 days via a scheduled Celery Beat job. Users can manually delete artifacts before expiry; org admins can bulk-delete. Expired artifacts are clearly indicated in the UI while job metadata remains visible. The job record is never deleted.

### Story 7.1: Scheduled Artifact Expiry & Cleanup

As an operator,
I want expired artifacts purged automatically every day,
So that storage does not grow unbounded while job history is preserved.

**Acceptance Criteria:**

**Given** a job that completed more than 10 days ago,
**When** the daily cleanup runs,
**Then** its artifact blobs (SBOM + all analysis reports) are deleted from the storage backend and `result_key` on the `SBOMJob` and `artifact_key` on every related `AnalysisReport` are nulled (FR-8.1, FR-8.2, AD-6).

**Given** the cleanup selector,
**When** it identifies expired jobs,
**Then** it uses `SBOMJob.objects.filter(artifacts_expire_at__lte=now(), result_key__isnull=False)` (AD-6 conventions).

**Given** any cleanup run,
**When** artifacts are deleted,
**Then** the `SBOMJob` record and its metadata (status, package count, summary statistics) are retained indefinitely — never deleted (FR-8.1).

**Given** the cleanup task,
**When** it is scheduled,
**Then** a Celery Beat entry runs it daily and the task routes to the `pipeline` queue (FR-8.2, AD-4).

**Given** the cleanup service function,
**When** it is invoked,
**Then** it is a pure service-layer function reused by both the scheduled task and on-demand deletion (Story 7.2), taking plain inputs (AD-3).

**Given** a job whose artifacts were already cleaned,
**When** the cleanup runs again,
**Then** it is skipped (its `result_key` is already null) — the operation is idempotent.

**Given** integration tests for the cleanup task,
**When** `pixi run cov` runs,
**Then** expiry selection, storage deletion, and key-nulling are covered ≥90%.

---

### Story 7.2: Manual & Bulk Artifact Deletion

As a user,
I want to delete a job's artifacts before the 10-day TTL, and as an admin delete all my org's artifacts,
So that I can reclaim storage or remove sensitive results on demand.

**Acceptance Criteria:**

**Given** a job owned by my org,
**When** I call `DELETE /api/v1/jobs/{task_id}/artifacts/`,
**Then** the shared cleanup service deletes the artifact blobs and nulls the keys; the job record is retained (FR-8.4).

**Given** a `DELETE` request for a job owned by another org,
**When** it is processed,
**Then** the response is `404` (AD-2).

**Given** I am an org admin,
**When** I trigger bulk-delete for the org,
**Then** all artifacts for all of the org's jobs are deleted and their keys nulled, while all job records are retained (FR-8.5).

**Given** a non-admin member,
**When** they attempt the org-wide bulk-delete,
**Then** the action is unavailable/forbidden (FR-8.5, AD-2).

**Given** a manual or bulk deletion,
**When** it completes,
**Then** it uses the same cleanup service function as the scheduled job (Story 7.1) — no duplicated deletion logic (AD-3).

**Given** artifacts already deleted for a job,
**When** a manual delete is requested again,
**Then** the operation succeeds idempotently with no error.

---

### Story 7.3: Expired-Artifact UI Indication

As a user,
I want clear notice when a job's artifacts are gone,
So that I understand why downloads are unavailable while still seeing the job's summary.

**Acceptance Criteria:**

**Given** a job whose artifacts have been deleted (expired or manual),
**When** I open its results page,
**Then** a notice states the artifacts are no longer available, including the expiry date, and download controls are disabled (FR-8.3).

**Given** an expired job on the results page,
**When** it renders,
**Then** the retained job metadata (status, package count, summary statistics) remains visible (FR-8.3).

**Given** an expired job in the job history dashboard,
**When** the list renders,
**Then** the row indicates artifacts are no longer available with the expiry date, while the job record stays in the list (FR-8.3).

**Given** the UI distinguishes an expired job from a failed job,
**When** both appear,
**Then** each shows its own distinct indication (expired-artifacts notice vs. failure reason) (FR-8.3, FR-7.3).

---

## Epic 8: SBOM Enrichment & In-App Viewing

Post-v1 enhancement epic driven by user feedback after the Epic 1–6 build and the
version-currency LTS fix. Three threads: (A) broaden LTS coverage using an external
end-of-life data source; (B) capture and surface the direct-vs-transitive dependency
distinction, which the current flat resolution discards; (C) let users read the SBOM
in the UI instead of only downloading it. Thread B leads with a design spike because
the mechanism differs per manifest format and per SBOM standard.

These extend the PRD's F4 (SBOM Generation), F5 (Analysis Reports), and F6 (Results
Web UI). New capability tags are prefixed `FR-E` (enhancement) to keep them distinct
from the v1 FR inventory above.

- FR-E1: The version-currency report derives each package's LTS series from the
  endoflife.date API (cached/rate-limited), falling back to the static registry;
  packages with no end-of-life data remain untracked (no false LTS claim).
- FR-E2: Resolution captures whether each resolved package is a direct (declared)
  dependency or a transitive one, per supported manifest format.
- FR-E3: The generated SBOM document encodes the direct/transitive relationship using
  the target standard's native mechanism (CycloneDX `dependencies`/scope; SPDX
  relationships).
- FR-E4: The dependency-graph tab visually distinguishes direct from transitive
  packages.
- FR-E5: A user can read the SBOM in the web UI — a component table and the raw
  document — without downloading it.

### Story 8.1: Broaden LTS Coverage via endoflife.date

As a user,
I want the version-currency report's LTS data to cover far more than Django and Python,
So that the "on LTS / LTS target" signal is useful across my real dependency set.

**Acceptance Criteria:**

**Given** a resolved package whose project is tracked on endoflife.date,
**When** the version-currency phase runs,
**Then** its LTS series is derived from the endoflife.date API (the latest cycle whose `lts` field is truthy), and `lts` / `on_lts` reflect that (FR-E1, extends FR-5.4).

**Given** the endoflife.date lookups,
**When** they are performed,
**Then** they go through the shared cached, rate-limited, retrying HTTP session (same pattern as OSV/PyPI/NVD) so repeated runs and shared packages don't re-hit the API (AD, NFR performance).

**Given** a package with no endoflife.date entry (or the API is unreachable),
**When** LTS is determined,
**Then** it falls back to the static `SBOM_LTS_REGISTRY` + built-in defaults, and if neither has it the package is reported untracked (`lts: null`, `on_lts: null`) — never a fabricated LTS.

**Given** a package name that differs from its endoflife.date product slug,
**When** the lookup is attempted,
**Then** a name→product mapping resolves the common cases and unmapped names simply fall through to untracked (no crash, no wrong match).

**Given** the endoflife.date integration,
**When** the LTS registry override or built-in default names a series for a package,
**Then** the explicit registry entry wins over the API-derived value (operator override is authoritative).

---

### Story 8.2: [Spike] Direct vs Transitive Dependency Design

As the team,
I want a short design decision on how to capture and represent direct-vs-transitive dependencies,
So that the implementation stories (8.3–8.5) build on one agreed mechanism instead of guessing.

**Acceptance Criteria:**

**Given** each supported manifest format (`requirements.txt`, `pyproject.toml`, `pixi.toml`, `pixi.lock`, `conda environment.yml`),
**When** the spike completes,
**Then** it documents how the *direct* (declared) set is identified for that format — e.g. `uv pip compile` annotations / `--no-annotate`, the declared lines pre-compile, `[project.dependencies]`, lock-file top-level requests — and the confidence/limitations of each.

**Given** the resolved data model,
**When** the spike completes,
**Then** it specifies how `PackageSpec` (and any threaded pipeline payload) carries the relationship (e.g. a `direct: bool` / `relationship` field) without breaking the existing chain contract (AD-6: keys/counts, not blobs).

**Given** the two SBOM standards in scope (CycloneDX, SPDX),
**When** the spike completes,
**Then** it documents the native representation of the direct/transitive relationship in each (CycloneDX `dependencies` graph + component `scope`; SPDX `DEPENDS_ON` / `DESCRIBES` relationships) and what our serializers must emit.

**Given** the spike's conclusions,
**When** it is written up,
**Then** it lands as a short design note (candidate architecture decision) in the planning artifacts and is cited by Stories 8.3–8.5, which are only then contexted into full story files.

---

### Story 8.3: Capture Direct/Transitive Relationships During Resolution

As a user,
I want the pipeline to know which packages I declared vs. which were pulled in transitively,
So that downstream (SBOM document, graph, viewer) can show the distinction.

**Acceptance Criteria (provisional — finalized by the 8.2 spike):**

**Given** a manifest in each supported format,
**When** transitive resolution runs,
**Then** every resolved `PackageSpec` is tagged direct or transitive per the mechanism chosen in 8.2 (FR-E2, extends FR-4.3).

**Given** the resolved list threads through the Celery chain,
**When** it is passed between phases,
**Then** the relationship tag travels with it within the existing contract (AD-6) and is unit-tested per format.

**Given** a format where the direct set cannot be determined reliably,
**When** resolution runs,
**Then** the behavior agreed in the 8.2 spike is applied (e.g. mark all as unknown/transitive) rather than a wrong guess, and is covered by a test.

---

### Story 8.4: Encode Direct/Transitive in the SBOM Document

As a user,
I want the downloaded/served SBOM to carry the direct/transitive relationship,
So that any consumer of the SBOM — not just this app — can tell them apart.

**Acceptance Criteria (provisional — finalized by the 8.2 spike):**

**Given** a CycloneDX (JSON/XML) output,
**When** the SBOM is generated,
**Then** the direct/transitive relationship is encoded via CycloneDX's native mechanism (dependencies graph and/or component scope) per the 8.2 decision (FR-E3, extends FR-4.4).

**Given** an SPDX output,
**When** the SBOM is generated,
**Then** the relationship is encoded via SPDX relationships per the 8.2 decision.

**Given** a generated SBOM,
**When** it is validated against its standard's schema,
**Then** it remains valid (the relationship encoding does not break conformance), covered by a test per format.

---

### Story 8.5: Direct/Transitive Visualization in the Dependency Graph Tab

As a user,
I want direct dependencies visually distinct from transitive ones in the graph,
So that I can see my declared surface at a glance.

**Acceptance Criteria (provisional — finalized by the 8.2 spike):**

**Given** the dependency-graph tab,
**When** it renders a job that carries the direct/transitive tag,
**Then** direct packages are visually distinguished from transitive ones (e.g. rooted/highlighted vs. faded) with a legend (FR-E4, extends FR-6.5).

**Given** an older job generated before this feature,
**When** its graph renders,
**Then** it degrades gracefully (no crash; renders without the distinction) rather than erroring.

---

### Story 8.6: In-App SBOM Viewer Tab

As a user,
I want to read the SBOM in the UI in a tab next to Overview,
So that I can inspect it without downloading and opening a file.

**Acceptance Criteria:**

**Given** a completed job,
**When** the results page loads,
**Then** an "SBOM" tab appears immediately to the right of Overview (FR-E5, extends FR-6.1).

**Given** the SBOM tab,
**When** it opens,
**Then** it shows a structured component table (at minimum name, version, type, license, and — once 8.3/8.4 land — direct/transitive) parsed from the stored SBOM, regardless of output format (cdx-json, cdx-xml, spdx) (FR-E5).

**Given** the SBOM tab,
**When** I toggle to the raw view,
**Then** it shows the exact SBOM document, pretty-printed and readable (syntax-highlighted / collapsible for JSON), matching what the download would produce (FR-E5).

**Given** the SBOM content is served to the SPA,
**When** the tab fetches it,
**Then** it comes from an inline content endpoint (JSON payload with a normalized component list + the raw text) via `src/api/` — not the `303`-presigned download flow — mirroring the inline report-endpoint pattern (AD-5, AD-11).

**Given** a job whose artifacts were never produced or have expired/been deleted,
**When** the SBOM tab renders,
**Then** it shows an appropriate unavailable/failure notice rather than erroring (FR-6.7, aligns with Epic 7).

**Given** a cross-org or unknown job,
**When** the SBOM content endpoint is called,
**Then** it returns `404` (AD-2).

---

### Epic 8 addendum — Package ecosystem & registry links

Follow-on to the version-currency work: surface whether each package comes from
**PyPI** or **Conda**, and link it to the right registry. The source is per-package
(pixi and conda manifests mix both), so it is captured at resolution time on
`PackageSpec` — the same shape as the direct/transitive flag (Story 8.3).

- FR-E6: Resolution captures each package's ecosystem (`pypi` | `conda`), and the
  version-currency report exposes it per package.
- FR-E7: The Version Currency tab marks each package PyPI/Conda and links its name
  to the registry detail page — pypi.org for PyPI, prefix.dev's conda-forge channel
  explorer for Conda.

Product decisions (from the requirements session): Conda `latest`/currency stays
PyPI-derived for now (flag + link only, no new Conda data source); Conda links
default to the **conda-forge** channel.

### Story 8.8: Capture Package Ecosystem (PyPI/Conda) During Resolution

As a user,
I want each resolved package flagged as PyPI or Conda,
So that the version-currency report can link it to the correct registry.

**Acceptance Criteria:**

**Given** the resolved `PackageSpec`,
**When** a manifest is resolved,
**Then** each spec carries an `ecosystem` field with value `pypi` or `conda` (default `pypi`) (FR-E6).

**Given** `requirements.txt` or `pyproject.toml`,
**When** resolved,
**Then** every package is tagged `pypi`.

**Given** `pixi.lock`,
**When** resolved,
**Then** each package is tagged from the lock's own conda-vs-pypi kind (conda packages `conda`, pypi packages `pypi`) — the clean per-package case.

**Given** `conda environment.yml`,
**When** resolved,
**Then** solver-resolved packages are tagged `conda` and any declared `pip:` entries `pypi` (best-effort).

**Given** `pixi.toml`,
**When** resolved,
**Then** packages declared under `[dependencies]` are tagged `conda` and `[pypi-dependencies]` plus transitive packages `pypi` (documented best-effort, since resolution flattens via `uv`).

**Given** the resolved list threads through the Celery chain,
**When** it passes between phases,
**Then** `ecosystem` travels with it (AD-6) and the version-currency report entry includes it.

### Story 8.9: Link Packages to PyPI / prefix.dev in the Version Currency Tab

As a user,
I want each package in the version-currency report marked PyPI/Conda and linked to its registry page,
So that I can jump straight to the package details.

**Acceptance Criteria:**

**Given** the Version Currency tab,
**When** it renders a package,
**Then** its ecosystem (`pypi`/`conda`) is shown as a small source indicator (FR-E7).

**Given** a PyPI package,
**When** its row renders,
**Then** the package name links to `https://pypi.org/project/{name}/{version}/`, opening in a new tab safely (`rel="noopener"`).

**Given** a Conda package,
**When** its row renders,
**Then** the package name links to `https://prefix.dev/channels/conda-forge/packages/{name}`, opening in a new tab safely.

**Given** a package with a missing/unexpected ecosystem,
**When** its row renders,
**Then** it degrades gracefully — the name is plain text, no broken link.

**Given** the link targets,
**When** they are built,
**Then** the URL is constructed from the report's `ecosystem` + name/version (no new network call; AD-5).

### Story 8.10: Capture conda-forge Latest & Flag PyPI/conda-forge Divergence

As a user,
I want the version-currency report to show the latest version on both PyPI and conda-forge and highlight when they differ,
So that I can see when conda-forge packaging is behind the PyPI release.

Refines the earlier "flag + link only" decision: we now capture conda-forge's latest
version for comparison. The currency *classification* (current/behind) stays
PyPI-based; conda-forge latest is an additional informational value with divergence
highlighting.

- FR-E8: For each package the report captures the latest conda-forge version
  alongside the PyPI latest, and flags when the two known latests differ.

**Acceptance Criteria:**

**Given** a package in the version-currency report,
**When** it is built,
**Then** the entry includes `conda_latest` (the latest conda-forge version) in addition to the existing PyPI `latest` (FR-E8).

**Given** a package not published on conda-forge (or the API is unreachable/returns bad JSON),
**When** conda-forge latest is looked up,
**Then** `conda_latest` is `null` and the phase never crashes (matches the PyPI-latest fallback behavior).

**Given** both the PyPI `latest` and `conda_latest` are known,
**When** they are not equal,
**Then** the entry flags divergence (e.g. `latest_mismatch: true`).

**Given** conda-forge lookups,
**When** performed,
**Then** they go through the shared cached, rate-limited session (like PyPI/endoflife.date), caching misses so untracked packages don't re-hit the API.

**Given** the Version Currency tab,
**When** a row renders,
**Then** it shows the conda-forge latest; and when it diverges from the PyPI latest, the conda-forge value is visually signified (e.g. rendered in an error/warning color) to indicate conda-forge is out of step.

**Given** the currency classification (current/behind-1/behind-2+),
**When** it is computed,
**Then** it remains PyPI-based — this story does not reclassify currency against conda-forge (out of scope; candidate future story).

### Epic 8 addendum — Metadata, Excel export, default sort & licenses UX

Post-review UX/reporting requests. New capability tags:

- FR-E9: The SBOM viewer shows a metadata block above the component table, and the
  generated SBOM places `metadata` before component data.
- FR-E10: Report tabs export to Excel — one `.xlsx` per tab, plus an Overview
  "export all" producing one workbook with a sheet per report.
- FR-E11: Each results tab opens pre-sorted in its most useful default order.
- FR-E12: The Licenses tab has Expand-all / Collapse-all controls for its tier groups.

Product decisions: default sorts — SBOM & Version Currency by package name,
Vulnerabilities by severity (unchanged), Licenses tier groups by risk
(copyleft → unknown → permissive). Excel: per-tab single-sheet files on each tab +
a combined workbook on Overview. Excel generation approach (client-side vs backend)
is decided in Story 8.12 and applied uniformly.

- **Story 8.11 — SBOM Metadata Block:** viewer shows metadata above the components;
  the document leads with `metadata` before components; content endpoint returns a
  parsed metadata object.
- **Story 8.12 — Export Version Currency to Excel:** per-tab `.xlsx` + the shared
  export mechanism reused by 8.13/8.14/8.15.
- **Story 8.13 — Export Vulnerabilities to Excel:** per-tab `.xlsx` (reuses 8.12).
- **Story 8.14 — Export Licenses to Excel:** per-tab `.xlsx` (reuses 8.12).
- **Story 8.15 — Overview Export All to Excel:** one workbook, a sheet per report.
- **Story 8.16 — Default Sort Order Per Tab:** SBOM/Version Currency by name,
  Vulnerabilities by severity, Licenses tier groups copyleft-first.
- **Story 8.17 — Licenses Expand All / Collapse All:** controls to open/close every
  risk-tier accordion at once.

---

## Epic 9: Project Management & CI/CD Workflows

Port the enabled GitHub workflows and project-management automation from the
reference component **millsks/idp-app** (`.github/`) into this repo, adapted to its
pixi umbrella toolchain (Python: ruff/mypy/pytest; frontend: oxlint/vitest; git-cliff
+ cliff.toml already present). One story per workflow, plus the label config and the
dev-tooling config.

**Explicitly excluded** (per direction): anything renovate (`renovate.json5`,
`renovate-runner.yml.disabled`) and the disabled workflows
(`update-pixi-lock-file.yml.disabled`, `renovate-runner.yml.disabled`).

External prerequisites are flagged per story (Codecov token, SonarCloud project +
`SONAR_TOKEN`, a GitHub App token for releases). Stories create the workflow/config;
the operator supplies the secrets.

- FR-CI1: A comprehensive CI workflow runs quality, tests (with coverage upload),
  builds, and a container build on push/PR.
- FR-CI2: Static analysis is reported to SonarCloud.
- FR-CI3: Releases are cut automatically (scheduled) and on demand, with a git-cliff
  changelog and a GitHub Release.
- FR-CI4: Scheduled repository maintenance prunes old workflow runs and runs a
  security audit.
- FR-CI5: Stale issues and PRs are managed automatically.
- FR-CI6: Issues and PRs are auto-labeled (by keyword, changed paths, and PR size).
- FR-CI7: Beneficial pixi tasks from idp-app (quality, security, Docker, hooks, changelog) are adopted.

### Story 9.1: Comprehensive CI Workflow

As a maintainer,
I want a full CI pipeline mirroring idp-app's,
So that every push/PR is quality-checked, tested with coverage, and built.

**Acceptance Criteria:**

**Given** a push or pull request,
**When** CI runs,
**Then** it executes (mirroring `idp-app/.github/workflows/ci.yml`, adapted): a
`concurrency` group; **backend-quality** (ruff lint, ruff format check, mypy, a
bandit security scan); **backend-test** (needs backend-quality) uploading coverage to
Codecov; **frontend-quality** (oxlint, `tsc` type check); **frontend-test** (needs
frontend-quality) uploading coverage to Codecov; **backend-build**; **frontend-build**;
and a **docker-build** that validates the image(s) build (FR-CI1).

**Given** the pixi umbrella toolchain,
**When** each job sets up,
**Then** it uses `prefix-dev/setup-pixi` and runs via `pixi run` tasks (no bespoke
Python/Node setup), consistent with the repo's harness.

**Given** the existing scaffold `ci.yml`,
**When** this lands,
**Then** it is expanded/replaced by the comprehensive workflow (keeping the
Python 3.12/3.13/3.14 matrix intent where sensible), and `pixi run ci` remains the
local gate.

**Given** Codecov upload,
**When** configured,
**Then** it uses `codecov/codecov-action@v5` and is documented as needing a Codecov
setup (token if the repo is private).

### Story 9.2: SonarCloud Code Analysis

As a maintainer,
I want SonarCloud static analysis on CI,
So that code quality/security issues are tracked over time.

**Acceptance Criteria:**

**Given** CI,
**When** the `sonar` job runs,
**Then** it invokes the SonarSource scan action against the project, publishing to
SonarCloud (FR-CI2).

**Given** the scan,
**When** it runs,
**Then** a `sonar-project.properties` (or equivalent) defines the project key, org,
sources (`backend/`, `frontend/src`), and coverage report paths.

**Given** external setup,
**When** the story is implemented,
**Then** it documents the prerequisites: a SonarCloud project and a `SONAR_TOKEN`
repository secret. (Story creates the workflow/config; operator provisions the token.)

### Story 9.3: Automated Release Workflow

As a maintainer,
I want scheduled and on-demand releases with a generated changelog,
So that versioned GitHub Releases are cut without manual steps.

**Acceptance Criteria:**

**Given** the release workflow (mirroring `idp-app/.github/workflows/release.yml`),
**When** it runs on its `schedule` or via `workflow_dispatch`,
**Then** it generates/updates the changelog with **git-cliff** (using the existing
`cliff.toml`), determines the next version, and publishes a **GitHub Release** via
`softprops/action-gh-release` (FR-CI3).

**Given** the release needs elevated permissions to push tags/commits,
**When** it authenticates,
**Then** it uses a GitHub App token (`actions/create-github-app-token`) — documented
as requiring an App ID + private key secret — rather than the default `GITHUB_TOKEN`
where branch protection requires it.

**Given** no releasable changes since the last release,
**When** the scheduled run executes,
**Then** it no-ops gracefully (no empty release).

### Story 9.4: Repository Maintenance Workflow

As a maintainer,
I want scheduled repository maintenance,
So that old workflow runs are pruned and dependencies are audited.

**Acceptance Criteria:**

**Given** the maintenance workflow (mirroring `idp-app/.github/workflows/maintenance.yml`),
**When** it runs on `schedule` / `workflow_dispatch`,
**Then** a **cleanup-artifacts** job prunes old workflow runs (e.g.
`Mattraks/delete-workflow-runs`) per a retention policy (FR-CI4).

**Given** the same workflow,
**When** it runs,
**Then** a **security-audit** job runs a dependency/security audit via pixi and
uploads the report as an artifact.

### Story 9.5: Stale Issue & PR Management

As a maintainer,
I want stale issues/PRs handled automatically,
So that the backlog stays current.

**Acceptance Criteria:**

**Given** the stale workflow (mirroring `idp-app/.github/workflows/stale.yml`),
**When** it runs on `schedule` / `workflow_dispatch`,
**Then** `actions/stale` marks and eventually closes stale issues and PRs per
configured days/labels/exempt rules (FR-CI5).

### Story 9.6: Label Automation

As a maintainer,
I want issues and PRs auto-labeled,
So that triage is consistent without manual labeling.

**Acceptance Criteria:**

**Given** the labeler workflow (mirroring `idp-app/.github/workflows/labeler.yml`),
**When** an issue or PR is opened/edited,
**Then** it applies labels by **keyword** (`github/issue-labeler` + `issue-labeler.yml`),
by **changed paths** (`actions/labeler` + `labeler.yml`), and by **PR size**
(`codelytv/pr-size-labeler`) (FR-CI6).

**Given** this repo's layout,
**When** the config files are ported,
**Then** `.github/labeler.yml` maps paths (`backend/**`, `frontend/**`,
`docker/**`+`docker-compose*.yml`, `.github/**`, `**.md`+`docs/**`, dependencies) and
`.github/issue-labeler.yml` maps keyword regexes (bug, enhancement, documentation,
question) — adapted to this repo.

**Given** the workflow needs the label set,
**When** implemented,
**Then** the referenced labels exist (documented as a one-time label bootstrap).


### Story 9.7: Adopt Beneficial Pixi Tasks from idp-app

As a maintainer,
I want the useful pixi tasks idp-app defines but we lack,
So that quality/security/Docker/release ergonomics match and the CI workflows have the tasks they call.

**Acceptance Criteria:**

**Given** `idp-app/pixi.toml`'s task set compared to ours,
**When** the beneficial tasks are adopted (adapted to our ruff/mypy/pytest/oxlint/vitest/Django/Celery/Docker stack),
**Then** we gain: `fmt-check` (ruff format --check) + `lint-fix`; `security` (bandit) + `fe-security` (npm audit); standalone `fe-typecheck` (tsc); `cov-html`; Docker convenience tasks (`docker-build/up/down/down-v/logs/ps/migrate/shell`); `flower` (Celery monitoring); `hooks-update` + commit-msg hook install; and `changelog-unreleased` — with new dev deps (bandit, flower) flagged, and `pixi run ci` still green (FR-CI7).

**Given** stack differences,
**When** adapting,
**Then** Prettier-based tasks are omitted (we use oxlint) and Alembic tasks are replaced by our Django `migrate`. Complements Story 9.1 (CI calls `fmt-check`/`security`/`fe-typecheck`).

---

## Epic 10: UI Navigation & Authenticated Routing

Today the SPA has routes but **no navigation UI** — users type `/register`, `/login`,
`/upload`, etc. into the address bar. And while a `ProtectedRoute` redirects
unauthenticated users to `/login`, it **loses the intended destination**, and the
login page doesn't return the user there. This epic adds a persistent, auth-aware
navigation shell and fixes the login round-trip. Frontend-only; reuses the existing
`OrgSwitcher` (Story 2.2), `ThemeModeProvider` (Story 5.7), and `api/auth.ts`/`api/orgs.ts`.

- FR-N1: A persistent navigation shell (top app bar) lets users reach every page
  without typing URLs, with the active route indicated.
- FR-N2: The nav is auth-aware (logged out → Login/Register; logged in → app links +
  org switcher + theme toggle + a user menu with Logout) and role-aware (admin-only
  links such as Members).
- FR-N3: Unauthenticated access to a protected page redirects to Login while
  preserving the intended destination.
- FR-N4: After a successful login the user is returned to the originally requested
  page (falling back to a sensible default).

### Story 10.1: App Shell & Auth-Aware Navigation

As a user,
I want persistent navigation in the UI,
So that I can move between pages by clicking instead of typing URLs.

**Acceptance Criteria:**

**Given** any page,
**When** it renders,
**Then** a persistent top app bar (shell layout wrapping the routes) shows the app
name/home link and the navigation for the current auth state, with the active route
visually indicated (FR-N1).

**Given** I am logged out,
**When** the nav renders,
**Then** it shows **Login** and **Register** (and no protected links).

**Given** I am logged in,
**When** the nav renders,
**Then** it shows the primary app links (Upload / New job, History, API Keys), the
**org switcher**, the **theme toggle**, and a user menu with **Logout**; **Members**
(and any other admin-only links) appear only for org admins (FR-N2).

**Given** shared auth state is needed by both the nav and route protection,
**When** implemented,
**Then** a single source of truth (e.g. an auth context/provider or hook) exposes
`authed` / current user / active org / `logout`, so the nav and `ProtectedRoute`
don't each re-derive it independently.

**Given** Logout,
**When** I click it,
**Then** the session ends (`api/auth.logout`) and I land on a public page (Home/Login)
with the nav updated to the logged-out state.

**Given** the shell,
**When** it wraps the routes,
**Then** `App.tsx` is refactored to render the pages inside the layout (nav +
`<Outlet/>`), without changing the existing route paths.

### Story 10.2: Redirect to Login and Back

As a user,
I want protected pages to send me to login and then back,
So that I return to where I was headed after signing in.

**Acceptance Criteria:**

**Given** I am not authenticated,
**When** I open a protected route (e.g. `/upload`, `/history`, `/results/:taskId`),
**Then** I am redirected to `/login`, and the **intended destination is preserved**
(router location state or a `?next=` param) (FR-N3).

**Given** I then log in successfully,
**When** the login completes,
**Then** I am redirected to the **originally requested page** — not a fixed default
(FR-N4).

**Given** I navigate to `/login` directly (no intended destination),
**When** I log in,
**Then** I land on a sensible default (e.g. dashboard/upload).

**Given** the redirect preserves state,
**When** implemented,
**Then** `ProtectedRoute` captures `location` on redirect and `LoginPage` reads it on
success; the round-trip is covered by a test.

**Given** I am already authenticated,
**When** I visit `/login`,
**Then** I am sent to the default authenticated page rather than shown the form again
(optional but recommended).
