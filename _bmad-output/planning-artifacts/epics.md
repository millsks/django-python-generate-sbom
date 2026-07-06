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

<!-- Epic 2 reopened (org membership model). Confirmed decisions: new users start with
     zero orgs; a system ADMIN org confers global-admin; global admins are FULL admins in
     ALL orgs (existing + future); existing global admins can grant global-admin; admins
     add EXISTING users by email. Story 2.6 is the anchor (the model change). -->

### Story 2.5: Create Organization from the UI

As a user,
I want to create a new organization from the app,
So that I can start a workspace without hitting the API directly.

**Acceptance Criteria:**

**Given** the backend `POST /api/v1/orgs/create/` (`CreateOrgView`) and `createOrg()`
already exist but are not exposed in the UI,
**When** a user creates an org,
**Then** a "Create organization" control (e.g. a "+ New organization" item in the org
switcher menu and/or a button on the Members page) opens a small dialog (org name),
calls `createOrg()`, and on success switches into the new org (FR — org creation UI).

**Given** a newly created org,
**When** it is created,
**Then** the creating user is its admin, and **all global admins are auto-added as
admins** of it (Story 2.8 provisioning) so oversight is preserved.

**Given** the org switcher,
**When** the new org exists,
**Then** it appears in the switcher and the user is scoped to it. Covered by a test.

### Story 2.6: Zero-Org Users & Identity Decoupled from the Active Org

As a newly registered user with no organization,
I want to be logged in and told what to do next,
So that I can create or join an org rather than hitting errors.

**Acceptance Criteria:**

**Given** registration currently auto-creates a "personal org" for every user,
**When** a normal user registers,
**Then** they start with **zero** orgs (no personal org is created); the **initial/
superuser** is instead seeded into the system **ADMIN** org (Story 2.8).

**Given** the app currently infers "logged in" from successfully fetching the active
org,
**When** a user has zero orgs,
**Then** authentication/identity is **decoupled from org membership** — a zero-org user
is still authenticated (via a user-identity signal, e.g. an `auth/me` endpoint / session
check, not `getActiveOrg`), so `AuthProvider`/`ProtectedRoute` no longer treat a no-org
user as anonymous.

**Given** the org-scoped pages (dashboard, upload, history, results, API keys),
**When** a user has no active org,
**Then** each shows a friendly **"You're not in an organization yet — create one or ask
an admin to add you"** empty state (with a create-org affordance) instead of erroring,
and the org switcher reflects the no-org state.

**Given** the change,
**When** complete,
**Then** tests cover: zero-org registration, a zero-org user staying authenticated, and
the no-org empty state; `pixi run ci` green.

### Story 2.7: Admin Adds/Removes Existing Users by Email

As an org admin,
I want to add existing users to my org by email and remove them,
So that I control who is a member.

**Acceptance Criteria:**

**Given** the current "Add member" creates a brand-new user with a temp password,
**When** an admin adds a member,
**Then** the primary flow **adds an existing user by email** to the org (looked up by
email); if no registered user matches, it returns a clear error (no auto-create for now).
Admin-gated (403 for non-admins / non-global-admins).

**Given** membership control,
**When** an admin removes a member,
**Then** the user is removed from that org (existing remove flow), respecting the edge
rules in Story 2.9; removing a user from their only org drops them to the zero-org state
(Story 2.6).

**Given** the Members page,
**When** used,
**Then** it exposes add-existing-by-email + remove for admins, with tests (add existing,
add-nonexistent error, remove, permission-gating).

### Story 2.8: Global Admin Org & Cross-Org Provisioning

As the platform owner,
I want a global-admin tier that oversees every organization,
So that platform admins can manage all orgs.

**Acceptance Criteria:**

**Given** the need for a global-admin tier,
**When** the model is defined,
**Then** a system **ADMIN** org exists (a distinguished `Org`, e.g. a flag/slug); its
members are **global admins**; the initial/superuser is seeded into it.

**Given** the confirmed provisioning rule,
**When** membership changes,
**Then** every global admin is a **full admin of ALL orgs, existing and future**: (a)
creating any org auto-adds all global admins as admins; (b) granting global-admin
(adding a user to the ADMIN org) **back-fills** that user as an admin into **all existing
orgs**.

**Given** who may grant global-admin,
**When** the ADMIN org is managed,
**Then** **existing global admins can add other users to the ADMIN org** (growing the
set), starting from the seeded superuser.

**Given** this is a cross-org superuser tier that bypasses normal org isolation,
**When** implemented,
**Then** the elevated access is deliberate and documented, permission checks treat global
admins as org admins everywhere, and tests cover: seeding, auto-add on org create,
back-fill on grant, and global-admin-only management of the ADMIN org.

### Story 2.9: Membership Edge Cases

As a maintainer,
I want membership edge cases handled safely,
So that orgs can't be left in a broken or orphaned state.

**Acceptance Criteria:**

**Given** an org's last admin,
**When** they try to leave or be removed,
**Then** it is prevented unless another admin (or a global admin) remains — or admin is
transferred first (existing `transfer-admin`).

**Given** an org with no members,
**When** the last member leaves/is removed,
**Then** the defined behavior applies (documented — delete the org, or leave it
admin-owned by global admins), consistently for normal orgs vs the system ADMIN org.

**Given** a global admin auto-added to every org,
**When** membership is edited,
**Then** a global admin isn't accidentally strandable (e.g. can't be the "last admin"
that blocks removal, since global admins are always present), and removing them from a
single org is handled per the global model (Story 2.8).

**Given** the rules,
**When** complete,
**Then** they are covered by tests and `pixi run ci` is green.

<!-- Epic 2 reopened again: Story 2.7 removed the admin's ability to onboard a brand-new
     person (create_member now raises no_such_user instead of creating). Story 2.10 restores
     new-user provisioning as an explicit, SEPARATE action that coexists with add-existing.
     Story 2.11 adds an admin-gated "Organization" control center to the side nav. -->

### Story 2.10: Admin Creates a New User Account (Restore New-User Provisioning)

As an org admin,
I want to create a brand-new user account and add it to my org in one step,
So that I can onboard someone who has not registered yet, instead of only adding people
who already have an account.

**Context (gap):** Story 2.7 changed the "Add member" flow to add an **existing** user by
email and made `create_member` raise `no_such_user` instead of provisioning an account
(`services.py:231-233`). That removed the only way an admin could onboard a brand-new person.
There is no email infrastructure, so the prior model applies: the admin sets a temporary
password and shares it out-of-band.

**Acceptance Criteria:**

**Given** an admin needs to onboard someone with no account,
**When** they use a new "create user" action (email + temporary password),
**Then** a **brand-new user is created and added to the active org** in one step — a **separate**
action from Story 2.7's add-existing-by-email, with **both coexisting** on the Members page.

**Given** the add-existing flow (Story 2.7),
**When** this story lands,
**Then** it is **unchanged**: "add existing" still raises `no_such_user` for an unregistered email;
only the new "create" action provisions an account.

**Given** a create request whose email is already registered,
**When** it is processed,
**Then** a clear error (`email_taken`) is returned — no silent duplicate, no fall-through to adding
the existing user — telling the admin to use "add existing" instead.

**Given** both actions,
**When** invoked,
**Then** they are admin-gated (org admin OR global admin; 403 otherwise), and tests cover create
success + membership, duplicate-email rejection, add-existing still raising `no_such_user`, and
permission gating.

### Story 2.11: Org Maintenance Navigation for Admins

As an org admin (or a global admin),
I want a clear "Organization" control center in the side navigation,
So that I have one obvious place to manage members, API keys, and org settings.

**Acceptance Criteria:**

**Given** the side navigation,
**When** the logged-in user is an admin of the active org **or** a global admin (`isAdmin` from
`useAuth`),
**Then** an **"Organization"** (org maintenance) entry is visible; a non-admin never sees it.

**Given** the entry,
**When** followed,
**Then** it leads to a clear place to administer the org — members (add-existing / create-new /
remove / make-admin), API keys, create org, and org info — built consistently with the existing
admin-gated nav (the Members link is already admin-gated, Story 10.1/12.3), either as a new
consolidated Organization page/route or an admin-gated nav group that reuses the existing
`MembersPage`/`KeysPage`.

**Given** the shell,
**When** the entry renders,
**Then** it uses the existing `NavIcon` vocabulary and active-route styling and closes the mobile
drawer via `onNavigate`, and tests assert it is present for an admin and absent for a non-admin.

<!-- Epic 2 reopened (bugfix): Story 2.12 restricts organization creation to GLOBAL admins only.
     User-reported issue + confirmed policy decision: self-service create-org (Stories 2.5/2.6) is
     DELIBERATELY REVERSED — a zero-org user now waits to be added by an admin instead of
     self-provisioning. Backend gates CreateOrgView on services.is_global_admin; frontend hides the
     create-org affordances for non-global-admins. Needs a new is_global_admin signal on auth/me +
     AuthProvider — coordinate with Story 10.5, which also extends auth/me + AuthProvider. 2.12 also
     folds in hiding the ADMIN org from the switcher (global-admin UX); Story 2.13 seeds the initial
     superuser from env vars. -->

### Story 2.12: Restrict Organization Creation to Global Admins (Bugfix)

As the product owner,
I want only global admins (members of the ADMIN org) to create organizations,
So that org provisioning is centrally controlled and regular users can't self-provision orgs.

**Context (bug / policy reversal):** Stories 2.5/2.6 shipped self-service org creation — any
authenticated user (including a zero-org user) can `POST /orgs/create/` and the UI offers "Create
organization" affordances everywhere. A user-reported issue plus a confirmed policy decision reverse
this: **only global admins** (`services.is_global_admin`, i.e. members of the ADMIN org where
`Org.is_admin_org=True`, Story 2.8) may create orgs. Regular users and ordinary org-admins **cannot**.
A zero-org non-admin now waits to be added by an admin (Story 2.7's add-by-email) rather than
self-provisioning. `CreateOrgView.post` (`views.py:242-248`) currently performs **no** global-admin
check, and the frontend surfaces create-org in four places.

**Acceptance Criteria:**

**Given** a request to `POST /orgs/create/`,
**When** the caller is **not** a global admin (a regular user or an ordinary org-admin),
**Then** the request is rejected with **403** (`not_global_admin`) and **no org is created**; when the
caller **is** a global admin the org is created as today (**201**), gating on `services.is_global_admin`.

**Given** the frontend needs to know global-admin status,
**When** `GET /api/v1/auth/me/` responds,
**Then** it includes an **`is_global_admin`** boolean and `AuthProvider` exposes it via `useAuth`
(this extends the same endpoint + provider as Story 10.5 — coordinate so both signals land together).

**Given** a non-global-admin user (including a zero-org user),
**When** the shell and org-scoped pages render,
**Then** **all** create-org affordances are hidden — `NoOrgState`'s "Create organization" button,
`OrgSwitcher`'s zero-org create button **and** its "New organization" menu item (Story 2.5), and
`OrganizationPage`'s create-org card (Story 2.11) — and a zero-org non-admin sees only an
"ask an admin to add you" empty state with **no** create button.

**Given** a global admin,
**When** the same surfaces render,
**Then** the create-org affordances remain available, and tests cover backend gating
(non-global-admin → 403, global admin → 201) and frontend visibility (hidden for non-global-admin,
shown for global admin).

**Given** the ADMIN org is a system org, not a workspace (and a global admin is auto-provisioned into
every org),
**When** the org switcher / org list renders,
**Then** the ADMIN org (`is_admin_org=True`) is **not** shown as a selectable org — it is filtered from
the org-listing path (`get_user_orgs` / `OrgListView`). A full global-admin management screen is out of
scope here (deferred to a later story).

<!-- Epic 2 (bugfix): Story 2.13 seeds the initial superuser from env vars so a fresh stack comes up
     with a global admin, without the manual createsuperuser step. -->

### Story 2.13: Seed the Initial Superuser from Environment Variables (Bugfix)

As an operator,
I want the initial superuser (global admin) seeded automatically from environment variables,
So that a fresh stack comes up with a global admin without a manual `createsuperuser` step.

**Context:** Today the first superuser must be created manually (`docker compose exec web pixi run python
backend/manage.py createsuperuser`); only then does the `create_superuser` hook make them a global admin
(Story 2.8). A fresh stack therefore starts with an empty ADMIN org and no one who can create orgs (Story
2.12), so nothing works until the operator runs the manual step. The `web` service already runs
`sh -c "pixi run migrate && pixi run web"` — a seed step slots in after `migrate`.

**Acceptance Criteria:**

**Given** `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` are set,
**When** the stack starts (after migrations),
**Then** an idempotent seed creates that superuser (if absent) via `createsuperuser --noinput` (or an
equivalent management command), making them a **global admin** through the existing `create_superuser` →
`grant_global_admin` hook.

**Given** the env vars are unset or the superuser already exists,
**When** the stack starts,
**Then** seeding is skipped cleanly (no error, no duplicate) — safe to run on every boot.

**Given** the compose / dev environment,
**When** documented,
**Then** the `web` service runs the seed after `migrate` and before `web`, and
`DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD` are documented in `.env.example`/README as a dev
convenience (never commit real credentials). Covered by a test of the seed command (idempotent create +
skip-when-exists).

<!-- Epic 2 (bugfix): 2.14 fixes the Create Organization dialog — the outlined "Organization name"
     field's floating label is clipped by DialogContent's too-small top padding. -->

### Story 2.14: Create-Organization Dialog Label Clipped (Bugfix)

As a user creating an organization,
I want the "Organization name" field label to be fully visible,
So that the dialog looks correct and the field is clearly labeled.

**Context:** In `CreateOrgDialog` the outlined `TextField`'s floating label is cut off (only its lower
half shows) because `DialogContent`'s `pt: 1` (8px) top padding is too small — the scroll area clips the
label, which sits above the input's top border.

**Acceptance Criteria:**

**Given** the Create Organization dialog is open,
**When** it renders,
**Then** the full "Organization name" label is visible above the outlined field (not clipped) —
`DialogContent` gives the label adequate top clearance (increased top padding and/or a top margin on the
field) — and the dialog's title spacing, error state, and actions still look correct.

**Given** the fix,
**When** complete,
**Then** the existing `CreateOrgDialog` render test still passes (label + fields present) and
`pixi run ci` is green.

<!-- Epic 2 (bugfix): 2.15 reorders the side navigation to Upload, History, Members, API Keys,
     Organization — interleaving the admin-only Members and Organization links into place. -->

### Story 2.15: Reorder the Left Side Navigation (Bugfix)

As a user,
I want the side-navigation destinations in a sensible order,
So that related items sit together and the admin links aren't appended out of place.

**Context:** `SideNav` builds `items = isAdmin ? [...NAV_ITEMS, ...adminItems] : NAV_ITEMS`, which appends
the admin-only Organization + Members links after API Keys — giving admins Upload, History, API Keys,
Organization, Members. The desired order interleaves them.

**Acceptance Criteria:**

**Given** an admin user,
**When** the side navigation renders,
**Then** the destinations are ordered **Upload, History, Members, API Keys, Organization** — Members
between History and API Keys, Organization last (both admin-only).

**Given** a non-admin user,
**When** the side navigation renders,
**Then** it shows Upload, History, API Keys (unchanged) with no Members/Organization links.

**Given** the change,
**When** complete,
**Then** `SideNav.test.tsx` asserts the admin order and `pixi run ci` is green.

<!-- Epic 2 reopened (bugfix): the admin workflow. 2.16 fixes "Make admin" — it now PROMOTES
     (adds an admin, demotes no one) instead of the old transfer that demoted the sole admin and
     could strip a global admin; the endpoint returns 204 (killing a false error). 2.17 enforces
     admin-only pages at the route AND the API (not just the nav), with auth/me carrying is_admin. -->

### Story 2.16: Fix "Make admin" — Promote, Don't Transfer; Protect Global Admins (Bugfix)

As an org admin,
I want "Make admin" to add another admin without demoting anyone,
So that I don't accidentally strip my own or the global admin's admin rights.

**Context:** "Make admin" was wired to `transfer_admin`, which promoted the target AND demoted the
caller when they were the sole admin — surprising for a promotion, and (for the seeded global admin)
it stripped their admin rights, violating Story 2.8. It also returned 200 with an empty body, which the
SPA turned into a false "Could not transfer admin." error while the change silently committed.

**Acceptance Criteria:**

**Given** an admin clicks "Make admin" on a member,
**When** it runs,
**Then** the target is promoted to admin of that org and **no one is demoted** (orgs may have many
admins), via `promote_member_to_admin` behind `POST /orgs/promote-admin/` returning **204**.

**Given** the promotion,
**When** it runs,
**Then** it is strictly per-org: it does NOT grant global admin, add the target to the ADMIN org, or
change their role in any other org — a promoted member is an admin of that one org only.

**Given** the buggy transfer,
**When** removed,
**Then** there is no demotion path, so a global admin can never be dropped below admin. Tests cover
promote-without-demote, per-org scoping (`is_global_admin` stays false; other-org role unchanged),
non-admin 403, non-member 400, and the frontend "Make admin" calling the promote endpoint.

### Story 2.17: Route + API Authorization for Admin Pages (Bugfix)

As a security-conscious operator,
I want admin-only pages enforced at the route and the API, not just hidden in the nav,
So that a non-admin can't reach them by typing the URL or calling the endpoint.

**Context:** `/members` and `/organization` used `ProtectedRoute` (authenticated-only), and
`MembersView.get` served the roster to any member — so authorization lived entirely in the hidden nav
links. A non-admin could open `/members` by URL and even call the API.

**Acceptance Criteria:**

**Given** a non-admin authenticated user,
**When** they navigate to `/members` or `/organization`,
**Then** an `AdminRoute` redirects them to `/` (anonymous → `/login`, preserving the destination).

**Given** the roster API,
**When** a non-admin calls `GET /orgs/members/`,
**Then** it returns **403 `not_admin`** (Members is an admin-only page now).

**Given** the client needs the admin flag cheaply,
**When** `GET /auth/me/` responds,
**Then** it includes `is_admin` (admin of the active org) and `AuthProvider` exposes `isAdmin` from it —
so nothing probes an admin-only endpoint to learn its role. Tests cover the redirect, the 403, and the
auth/me flag; `pixi run ci` is green.

<!-- Epic 2 reopened (bugfix): user-reported access-control gaps. 2.18 restricts a zero-org user to
     the home page and stops the system ADMIN org ever acting as a working org (the session path now
     excludes it, matching the fallback). 2.19 hides the org switcher unless there is more than one org
     to switch between. 2.20 adds the missing inverse of "Make admin" — demote an admin back to member
     (guarded so the org keeps ≥1 admin and global admins stay admins). All three overlap Story 13.1
     (routes, OrgSwitcher, AuthProvider, MembersPage, users backend) and are implemented AFTER 13.1. -->

### Story 2.18: Restrict Zero-Org Users to the Home Page; the ADMIN Org Is Never a Working Org (Bugfix)

As a signed-in user with no organization (and as a global admin),
I want to only reach the home page and never have the system ADMIN org act as my workspace,
So that I can't upload or view history "in" an org I don't really work in.

**Context:** `get_request_org`'s fallback already excludes the ADMIN org (Story 2.12), but its **session
path** (`memberships.filter(org_id=active_id)`) does not — so a pinned `active_org_id` at the ADMIN org
still resolves it as the active org, letting a global admin (a member of the ADMIN org) work "in" Admin.
The home "Upload a manifest" CTA is unconditional, and org-scoped pages render `NoOrgState` but are still
reachable by a zero-org user (no redirect).

**Acceptance Criteria:**

**Given** any user (including a global admin) with a pinned `active_org_id`,
**When** `get_request_org` resolves the active org,
**Then** the ADMIN org is never returned — the session path validates the pinned id against a NON-admin
membership (as the fallback already does), so a user whose only membership is the ADMIN org resolves to
**no active org** (zero-org).

**Given** an authenticated user with no active org,
**When** they hit any org-scoped route (`/upload`, `/history`, `/keys`, `/members`, `/organization`,
`/results/*`),
**Then** a route guard REDIRECTS them to `/` (home); only home (plus `/login`, `/register`, and any
global-admin screen) is reachable — enforced at the route, not just the per-page `NoOrgState`.

**Given** a zero-org user on the home page,
**When** it renders,
**Then** there is NO "Upload a manifest" CTA; instead the `NoOrgState` copy ("ask an admin to add you")
is shown. Backend org-scoped endpoints keep denying with no active org (defense in depth). Tests cover
the ADMIN org never being active (session + fallback), the zero-org redirect, and the hidden home CTA.

### Story 2.19: Hide the Org Switcher When the User Has One or Fewer Orgs (Bugfix)

As a user who belongs to a single organization,
I want no pointless org-switcher dropdown,
So that the header only offers a switch control when there is actually something to switch to.

**Context:** `OrgSwitcher` renders the dropdown whenever `orgs.length > 0`, so a user with exactly one
org gets a `Select` with a single item and nothing to switch to. `getOrgs()` already returns only
non-ADMIN orgs (`get_user_orgs`), so the fix is a length check of `> 1`.

**Acceptance Criteria:**

**Given** a user with more than one switchable (non-ADMIN) org,
**When** the switcher renders,
**Then** the dropdown appears with a `MenuItem` per org. With exactly one org, no dropdown — the org
name is shown statically (or the control omitted; the active org already appears in the account menu and
side-nav footer). With zero orgs, no dropdown.

**Given** the create-org affordance,
**When** the switcher renders,
**Then** it stays **global-admin-only** (Story 2.12) — a non-admin never sees it; a user who sees it IS a
global admin. This story does not loosen that gate.

**Given** the change,
**When** complete,
**Then** tests cover `>1` org → dropdown, exactly `1` → no dropdown (name shown), `0` → create affordance
only for a global admin; `pixi run ci` is green.

### Story 2.20: Admin Can Demote Another Admin to Member (Bugfix)

As an org admin,
I want to demote another admin back to a member without removing them from the org,
So that I can correct an over-promotion without kicking the person out.

**Context:** The Members page only offers "Remove" and (on non-admin rows) "Make admin"; there is no way
to drop an admin back to `member` while keeping them in the org. "Make admin" (Story 2.16,
`promote_member_to_admin`) promotes, but has no inverse — demotion existed only inside the removed
`transfer_admin`.

**Acceptance Criteria:**

**Given** an admin demotes another admin,
**When** it runs,
**Then** a new `demote_admin_to_member(org, target)` sets that org's membership `role = member` for that
org only (no other-org effect), via an admin-gated `POST /orgs/demote-admin/` with `{user_id}` returning
**204** — mirroring `promote-admin/`.

**Given** the demote,
**When** the target is the org's last admin or a global admin,
**Then** it is blocked: `LastAdminError` (the org must keep ≥1 admin) or `GlobalAdminError` (global admins
stay admins of every org — Stories 2.8/2.9), each surfaced with distinct UI copy.

**Given** the Members page,
**When** it renders an `admin`-role row,
**Then** a "Make member" action sits beside "Remove", wired to the demote endpoint.

**Given** any membership action (remove, promote, demote) fails,
**When** the backend returns a specific error code,
**Then** the page shows that specific reason instead of a generic "Could not …" — `handleRemove` /
`handlePromote` / `handleDemote` map `global_admin_protected`, `last_admin`, `admin_org_protected`,
`not_a_member` (and `no_such_user`) to clear copy (reusing `handleAdd`'s pattern), falling back to the
backend message. Tests cover the promote↔demote round-trip, blocked last-admin and global-admin demotes,
per-org scoping (a two-org admin's other-org role unchanged), a non-admin caller → 403, and a
`global_admin_protected` remove/demote surfacing its specific reason.

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

> **Reopened (bugfix):** Story 6.4 fixes a user-reported defect on the History page — selecting a real manifest format (`pixi_toml`) in the **Manifest format** filter replaces the jobs table with the "Could not load your jobs." error banner. The jobs-list request fails on a value the UI legitimately offers, because the frontend format options (`HistoryPage.tsx`) and the backend accepted formats (`ManifestUpload.Format`) are maintained independently and can drift — and because the backend filter does not degrade gracefully on an unrecognized value. Coordinates with Story 11.19 (documents the `format` query param + allowed values in the OpenAPI schema) and Epic 8's pixi/conda formats (8.18/8.19); implement against the then-current merged state.

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

### Story 6.3: Job Elapsed Time on the History Page

As a user,
I want to see how long each job took to complete,
So that I can gauge processing time and spot slow runs at a glance.

**Acceptance Criteria:**

**Given** a completed (or failed) job,
**When** the jobs list is served,
**Then** the API exposes the job's total elapsed time — the wall-clock duration from
`created_at` to `completed_at` — as a computed field (e.g. `elapsed_seconds`), null while
the job is still running or if `completed_at` is unset.

**Given** the History dashboard table,
**When** it renders,
**Then** it shows an **Elapsed** (duration) column, human-formatted (e.g. `1m 23s`,
`2h 05m`, `450ms`), for finished jobs; a still-running job shows a live/updating
elapsed (from `created_at` to now) or a dash, consistent with the existing 5s polling.

**Given** the table already supports sorting,
**When** the Elapsed column is added,
**Then** it fits the existing column/sort conventions (sortable if the table sorts other
columns), without disrupting the current columns or live-progress behavior (Story 6.2).

**Given** the change,
**When** complete,
**Then** it is covered by tests: the serializer's `elapsed_seconds` computation
(including the null-while-running case) and the table's formatted rendering, and
`pixi run ci` is green (backend coverage ≥90%).

---

### Story 6.4: Fix the Manifest-Format Filter on the History Page (Bugfix)

As a user,
I want to filter my SBOM jobs by any manifest format the History page offers,
So that selecting a real format (e.g. `pixi_toml`) shows the matching jobs instead of an error.

**Acceptance Criteria:**

**Given** the History page ("Your SBOM jobs") with the **Manifest format** filter,
**When** I select any format the dropdown offers — explicitly `pixi_toml`, and each of the other current formats (`requirements`, `pyproject`, `pixi_lock`, `conda`) —
**Then** `GET /api/v1/sbom/jobs/?format=<value>` returns `200` with only the jobs whose manifest matches that format, and the table renders those rows — the "Could not load your jobs." error banner never appears.

**Given** the **Manifest format** filter set to **All**,
**When** the jobs list is served,
**Then** the behavior is unchanged — all of the org's jobs are returned regardless of manifest format (no regression).

**Given** the backend jobs-list filter,
**When** it receives an unknown or invalid `format` value,
**Then** it degrades gracefully — an empty result set (or the value is ignored) — and never returns a `400`/`500`, so a stale UI can never turn a filter selection into the error banner.

**Given** the frontend format options and the backend accepted formats,
**When** the manifest-format list changes (e.g. Epic 8's pixi/conda work adds or renames a format),
**Then** both derive from one canonical source (the backend's `ManifestUpload.Format` codes), so the UI can never offer a value the backend rejects; a test asserts the two stay consistent so drift fails CI.

**Given** the change,
**When** complete,
**Then** it is covered by tests: a backend test asserting `GET /api/v1/sbom/jobs/?format=pixi_toml` returns the matching job(s) with `200` (and an invalid value degrades cleanly, not a `500`), and a frontend test asserting that selecting a format issues the request with the right `format` param and renders results rather than the error state; `pixi run ci` is green (backend coverage ≥90%).

---

## Epic 7: Artifact Retention & Lifecycle Management

Generated artifacts are automatically purged after 10 days via a scheduled Celery Beat job. Users can manually delete artifacts before expiry; org admins can bulk-delete. Expired artifacts are clearly indicated in the UI while job metadata remains visible. The job record is never deleted.

### Story 7.1: Scheduled Artifact Expiry & Cleanup

As an operator,
I want expired artifacts purged automatically every day,
So that storage does not grow unbounded while job history is preserved.

**Acceptance Criteria:**

**Given** a job whose artifacts have passed the configured retention period,
**When** the daily cleanup runs,
**Then** its artifact blobs (SBOM + all analysis reports) are deleted from the storage backend and `result_key` on the `SBOMJob` and `artifact_key` on every related `AnalysisReport` are nulled (FR-8.1, FR-8.2, AD-6).

**Given** the retention window,
**When** `artifacts_expire_at` is computed (at job creation/completion),
**Then** it uses a configurable retention period that **defaults to 30 days** and is overridable via a setting / env var (e.g. `ARTIFACT_RETENTION_DAYS`), so operators can change it without a code change.

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

### Story 8.18: [Spike] Resolve conda environment.yml via pixi conversion

As a maintainer,
I want to validate resolving a conda `environment.yml` by converting it to a pixi
manifest and solving with pixi (instead of shelling out to mamba/conda),
So that conda resolution runs through the project's native toolchain and reuses the
existing pixi.lock parser.

**Context:** The current conda resolver (`sbom/parsers/_conda.py`) shells out to
`mamba env create --dry-run --json`. It works, but it adds heavy `conda`+`mamba`
runtime deps, resolves conda-forge via `conda.anaconda.org` (not prefix.dev), and is a
second, separate resolution path. `pixi init --import environment.yml` (verified with
pixi 0.72.0) converts an env file to a pixi manifest cleanly (conda deps →
`[dependencies]`, nested `pip:` → `[pypi-dependencies]`, channels preserved, with a
`--conda-pypi-map` option). pixi's own solver (rattler, from prefix.dev) can then solve
it, and the repo already has a `pixi.lock` parser (`sbom/parsers/pixi_lock.resolve`).

**Acceptance Criteria:**

**Given** a range of real `environment.yml` files (simple; with a `pip:` block; with
build strings and multi-constraint version specs),
**When** each is converted with `pixi init --import` and solved with `pixi lock`,
**Then** the spike records whether the conversion is faithful (specs, channels, pip
extras) and whether `pixi lock` produces a `pixi.lock` that `pixi_lock.resolve` parses
into the expected `PackageSpec` list (name, version, direct/transitive, ecosystem).

**Given** an `environment.yml` declares no platform,
**When** pixi solves,
**Then** the spike decides which platform(s) to solve for (the worker's platform vs. a
configurable/canonical target) and documents the choice.

**Given** genuinely unsatisfiable inputs (e.g. CUDA-only builds, private packages not
on conda-forge — like the observed `farm-environment.yaml`),
**When** solved via pixi,
**Then** the spike confirms they still fail (as expected) and captures how pixi surfaces
the reason, so Story 8.19 can present a clear failure message instead of an opaque
`resolution_failed`.

**Given** the outcome,
**When** the spike concludes,
**Then** it gives a go/no-go plus the recommended implementation shape for Story 8.19,
including whether `conda`+`mamba` can be dropped as runtime deps.

### Story 8.19: Resolve conda environment.yml via pixi (replace the mamba solver)

As a user,
I want conda `environment.yml` uploads resolved through pixi,
So that they use the project's native toolchain, reuse the pixi.lock parser, and drop
the mamba/conda dependency — while genuinely unsolvable environments fail with a clear
reason.

**Acceptance Criteria:**

**Given** the spike's go decision (Story 8.18),
**When** the CONDA resolver is reworked,
**Then** `sbom/parsers/conda.resolve()` converts the uploaded `environment.yml` to a
pixi manifest (via `pixi init --import` or equivalent), solves it with `pixi lock` (in
an isolated temp dir, no install — solve only), and parses the resulting `pixi.lock`
into `PackageSpec`s, reusing `pixi_lock.resolve` (or shared logic) so conda ecosystem +
direct/transitive tagging are preserved.

**Given** the mamba/conda subprocess is no longer used,
**When** the change lands,
**Then** `sbom/parsers/_conda.py` (the mamba/conda path) is removed and `conda` +
`mamba` are dropped from `pixi.toml` runtime dependencies.

**Given** a solvable `environment.yml`,
**When** it is uploaded,
**Then** the SBOM job completes with the expected resolved package list (no
`resolution_failed`), verified by tests.

**Given** a genuinely unsatisfiable `environment.yml` (CUDA-only builds, private/
off-conda-forge packages),
**When** it is resolved,
**Then** the job fails deliberately (still a `ResolutionError`), but the failure reason
surfaces the actual solver problem (e.g. "nothing provides __cuda …") rather than an
opaque status — so the UI can explain why.

**Given** the pipeline and tests,
**When** complete,
**Then** `pixi run ci` is green (backend coverage ≥90%), with unit tests mocking the
pixi solve for a solvable and an unsatisfiable case, and the detection/format wiring for
`environment.yml`/`.yaml` is unchanged.

### Story 8.20: [Deferred] Configurable conda solve platform & CUDA system-requirement

As a maintainer,
I want the conda resolver's target platform and CUDA assumption to be configurable,
So that resolution behavior can be adjusted without a code change if requirements change.

**Deferred — parked for later per an explicit decision; the current fixed defaults
(`linux-64` + `cuda="12"`) are intentional and stay as-is until this is picked up.**

**Context:** Story 8.19's pixi-based conda resolver hard-codes `--platform linux-64`
and appends a `cuda="12"` system-requirement (this is what lets CUDA environments such
as `farm-environment.yaml` resolve — `linux-64` alone still fails `nothing provides
__cuda`). Both are deliberate fixed defaults for now. This story exists only so the
choice can be revisited if a per-deployment or per-request need emerges.

**Acceptance Criteria (when/if implemented):**

**Given** the conda solve platform,
**When** made configurable,
**Then** it is overridable via a setting/env var (e.g. `CONDA_SOLVE_PLATFORM`),
**defaulting to `linux-64`** so current behavior is unchanged.

**Given** the CUDA system-requirement,
**When** made configurable,
**Then** it is overridable/toggleable via a setting/env var (e.g. `CONDA_SOLVE_CUDA`),
**defaulting to `12`** (enabled), with an option to omit it for non-CUDA-only targets.

**Given** the change,
**When** complete,
**Then** the defaults are unchanged, tests cover the overrides, and `pixi run ci` stays
green.

### Story 8.21: Fix the PyPI → conda-forge equivalent (reverse) lookup

As a user,
I want a PyPI package mapped to its correct conda-forge package,
So that the conda-forge latest / divergence lookup compares against the right package
(not a coincidentally same-named but unrelated one).

**Context (bug):** parselmouth's mapping is authoritative in the conda→PyPI direction.
The reverse map (`parselmouth._ensure_loaded`) builds PyPI→conda by inverting it, but it
**"prefers an identity mapping (conda name == pypi name) when several exist"**
(`parselmouth.py:62-63`). That heuristic is wrong when the same-named conda package is a
*different* project: e.g. PyPI **`build`** should map to conda-forge **`python-build`**,
but conda-forge also has an unrelated **`build`** package, so the identity rule
overrides `python-build` with `build`. `pypi_to_conda("build")` then returns `build`,
and `versions._conda_forge_latest` (versions.py:172) queries the wrong conda-forge
package.

**Acceptance Criteria:**

**Given** a PyPI name whose true conda-forge equivalent has a different name,
**When** `parselmouth.pypi_to_conda(name)` is called,
**Then** it returns the correct conda-forge package — e.g. `pypi_to_conda("build")` →
`python-build` — rather than the coincidentally same-named package.

**Given** the faulty "prefer identity" tie-break,
**When** the reverse map is rebuilt,
**Then** that heuristic is removed/replaced so a same-named-but-unrelated conda package
no longer overrides the authoritative equivalent; a small **curated override table**
(seeded with `build → python-build`, extendable) resolves known ambiguous PyPI→conda
cases, and normal 1:1 names (e.g. `numpy → numpy`) are unaffected.

**Given** the conda-forge latest / divergence feature (Story 8.10),
**When** it looks up a PyPI package's conda-forge counterpart,
**Then** it uses the corrected mapping, so the conda-forge latest and the
PyPI/conda-forge divergence flag are computed against the right package.

**Given** the fix,
**When** complete,
**Then** tests cover the `build → python-build` case, the identity/1:1 case, and the
override precedence, and `pixi run ci` is green (backend coverage ≥90%). conda-forge
data continues to come from **prefix.dev**, not anaconda.

<!-- Epic 8 reopened: Story 8.22 carries the Version Currency tab's red "conda-forge latest"
     divergence text into the Excel export so mismatches stay identifiable in the spreadsheet.
     Frontend-only; extends the 8.12 export (reportSheets/excelExport) using the same
     latest_mismatch condition the 8.10 UI uses. -->

### Story 8.22: Version-Currency Excel Export Carries the conda-forge-Latest Text Color

As a user exporting the version currency report to Excel,
I want the "conda-forge Latest" cell to be red when it diverges from the PyPI latest,
So that mismatches stay identifiable in the spreadsheet exactly as they are in the UI.

**Context (bug):** the Version Currency tab renders the conda-forge-latest text in **red**
when it diverges from the PyPI latest (Story 8.10), but the Excel export (Story 8.12) copies
the value as plain text and loses that signal — `versionCurrencySheet` emits
`conda_latest: pkg.conda_latest ?? ''` with no styling (`reportSheets.ts:30`), and
`buildWorkbook` only styles hyperlink cells (`excelExport.ts:37-39`).

**Acceptance Criteria:**

**Given** an exported version-currency `.xlsx`,
**When** a "conda-forge Latest" cell diverges from the PyPI latest,
**Then** that cell is rendered with a **red font**, mirroring the UI's red divergence text.

**Given** the UI's red-text rule,
**When** the export decides which cells to color,
**Then** it uses the **same** condition the UI uses — `latest_mismatch === true` on the version
entry (`VersionsTab.tsx:179`, `api/reports.ts:62`) — so the export and the on-screen table always
agree on which cells are flagged; non-mismatch and empty conda values keep the default font.

**Given** the fix,
**When** complete,
**Then** a test asserts a mismatched conda-forge-latest cell in the generated sheet has the red
font (and a non-mismatched cell does not), and `pixi run ci` is green.

<!-- Epic 8 reopened: Story 8.23 puts the PyPI-latest and conda-forge-latest columns side by
     side in the version currency table (and matches the export), renaming "Latest" to
     "PyPI Latest" for at-a-glance comparison. Frontend-only; independent of 8.22's red font. -->

### Story 8.23: Version Currency — Side-by-Side PyPI / conda-forge Latest Columns

As a user reading the version currency report,
I want the "PyPI Latest" and "conda-forge Latest" columns to sit next to each other,
So that I can compare the two latest versions at a glance without scanning across the other columns.

**Context:** the version currency table shows a "Latest" column (the **PyPI** latest —
`VersionEntry.latest`, `api/reports.ts:56`; the export already labels it "Latest (PyPI)",
`reportSheets.ts:18`) separated from "conda-forge Latest" by the Status column
(`VersionsTab.tsx:31-36,159-161`). Placing the two latest columns adjacent makes PyPI-vs-conda
comparison direct.

**Acceptance Criteria:**

**Given** the version currency **table**,
**When** it renders,
**Then** the "Latest" column is moved to sit immediately **left** of "conda-forge Latest" and its
header is renamed to **"PyPI Latest"**, so the two latest columns are adjacent in the order
**PyPI Latest | conda-forge Latest**.

**Given** the renamed column's source,
**When** labelled,
**Then** it genuinely shows the **PyPI** latest (verified against `VersionEntry.latest`), so
"PyPI Latest" is accurate.

**Given** the version-currency Excel export and the Overview "export all" workbook (both via
`versionCurrencySheet`),
**When** they are generated,
**Then** they use the **same** column order and the **"PyPI Latest"** header, so UI and exports match.

**Given** the reorder,
**When** complete,
**Then** the default per-tab sort (Story 8.16) still targets its intended column and Story 8.22's
conditional red font on the conda-forge-latest cells is unaffected; tests assert the tab renders
"PyPI Latest" immediately before "conda-forge Latest" and the export sheet has that order + label, and
`pixi run ci` is green.

<!-- Epic 8 reopened (bugfix): 8.24 fixes wrong conda-forge lookups where a PyPI name coincides with an
     unrelated same-named conda-forge package (often a C library). The authoritative answer is
     parselmouth's "conda package that reports PyPI metadata for X" (prefix-dev.github.io/parselmouth,
     ?dir=pypi) — e.g. PyPI xxhash -> conda-forge python-xxhash. Use that real mapping data, not a
     name-shape guess; investigate whether the mapping is even loaded (weekly refresh + MinIO). -->

### Story 8.24: Fix PyPI → conda-forge python-<name> Disambiguation (Bugfix)

As a user reading the version-currency report,
I want the conda-forge column to resolve to the correct package when a PyPI name collides with a
non-Python conda-forge package,
So that version mismatches aren't reported against the wrong conda-forge package.

**Context:** `parselmouth.pypi_to_conda` (`backend/generate_sbom/analysis/services/parselmouth.py`)
resolves a PyPI name via a curated override map, then the inverted parselmouth map with **"first mapping
wins"**, then a **same-name fallback**. Parselmouth's authoritative answer is "the conda-forge package
that reports PyPI metadata for X" — for PyPI **xxhash** that is **python-xxhash**, not the unrelated
same-named C library `xxhash`. The mapping (`compressed_mapping.json`) is refreshed **weekly** into
storage with **no bundled copy**, so before a refresh only a 3-entry seed is present and everything else
same-name-falls-back — a likely reason `xxhash` resolves wrong in practice. Root cause must be confirmed
against the real data before fixing.

**Acceptance Criteria:**

**Given** parselmouth's `compressed_mapping.json` (33,415 entries) is loaded as a baseline from first boot
— not just the 3-entry seed,
**When** `pypi_to_conda(name)` resolves an unambiguous PyPI name,
**Then** it returns the correct conda-forge package (e.g. `xxhash → python-xxhash`, since the map has
`python-xxhash → xxhash` and `xxhash → None`); this fixes the ~19,700 single-match names that previously
same-name-fell-back because the weekly refresh hadn't populated the map.

**Given** a PyPI name with more than one conda candidate (~297 of ~20,000, e.g. `build → build` AND
`python-build → build`),
**When** it is resolved,
**Then** parselmouth's authoritative per-package data (`pypi-to-conda-v1/conda-forge/<name>.json`, latest
release) decides it (`build → python-build`) — a cached lookup only for ambiguous names — with
`_PYPI_TO_CONDA_OVERRIDES` as the highest-precedence fast path and a deterministic fallback if the
per-package lookup fails.

**Given** existing behavior,
**When** the fix lands,
**Then** renames still resolve (`torch → pytorch`) and single-match names are unchanged
(`requests → requests`); unit tests (no live network; per-package mocked) cover xxhash, an ambiguous name,
a passthrough, override precedence, and per-package failure, and `pixi run ci` is green.

---

### Story 8.25: Include License in the SBOM Document (Bugfix)

As a user reading the SBOM Results page,
I want each component in the generated SBOM document to carry its license,
So that the SBOM tab's Components table License column (and the raw SBOM blob) show the license
instead of "—", matching what the Licenses tab already reports.

**Context:** User-reported gap (screenshot confirmed). The **SBOM tab → Components** table's License
column shows "—" for every package, while the **Licenses tab** correctly captures and shows each
package's license. The two read the same-named `license` field from different sources: the Licenses
tab reads the enriched Phase 5 compliance report; the SBOM tab reads the license parsed back out of
the **stored SBOM document** (`sbom/document.py::normalize_components`), which the generator
(`sbom/generation.py`) never populated. Story 8.6 flagged this exactly as a known caveat ("the
current SBOM generator does not embed per-component licenses … kept for when generation is
enriched"). This story is that enrichment. **Ordering (AD-6):** Phase 3 (generate) already writes the
SBOM blob; Phase 5 (license compliance) runs after it and Phase 8 only finalizes the DB — so the
license is resolved and written **at Phase 3 generation time** using the **same** normalization
Phase 5 uses (`analysis/services/license.py::_extract_license`, PyPI metadata: PEP 639
`license_expression` → Trove classifiers→SPDX → free-text, over the shared 1h-cached `pypi_session`).
No downstream blob rewrite; the persisted blob is not touched after Phase 3.

**Acceptance Criteria:**

**Given** a resolved package whose license is determinable from PyPI metadata,
**When** Phase 3 generates the SBOM document,
**Then** the component carries the license — CycloneDX 1.6 `component.licenses` (SPDX id, SPDX
expression, or a named `License` for free-text) via `cyclonedx-python-lib`'s `LicenseFactory`; SPDX
2.3 `licenseConcluded`/`licenseDeclared` — for `cdx-json`, `cdx-xml`, and `spdx-2.3` (extends FR-4.4).

**Given** a package whose license cannot be determined (no metadata, non-classifiable free text, or a
PyPI fetch failure),
**When** the SBOM is generated,
**Then** the component is emitted with no license entry (CycloneDX) / `NOASSERTION` (SPDX) and
generation never raises — the rest of the SBOM still builds.

**Given** the enriched SBOM document,
**When** the SBOM tab loads,
**Then** the Components table License column populates from the document (via the existing
`normalize_components` → `SbomTab` path — no viewer change) and the Raw view shows the same license;
and the SBOM license equals the Licenses tab value because both derive from the one shared
normalization (no divergence).

**Given** the storage triad (AD-6),
**When** the license is added,
**Then** it is written into the SBOM at Phase 3 (which already writes the blob); the blob is not
rewritten downstream, Phase 8 still only finalizes the DB, and no blob flows through the Celery result
backend. (Any need to change this boundary is a flagged deviation for approval, not a silent change.)

**Given** the change,
**When** it is verified,
**Then** a backend unit test asserts the generated CycloneDX components include `licenses` for
known-license packages and omit it cleanly for unknown ones (and the SPDX path sets
`licenseConcluded`/`NOASSERTION`); a frontend test asserts the Components table renders a license and
shows "—" for a null-license component; and `pixi run ci` is green.

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

<!-- Epic 10 reopened: Story 10.3 adds a post-registration auto-redirect to login so users
     don't have to click the login link manually. Frontend-only; reuses the existing
     registration flow (api/auth.register) and react-router navigation. Independent of the
     Epic 2 registration-response change (2.6) — this is navigation-after-success only. -->

### Story 10.3: Auto-Redirect to Login After Registration

As a newly registered user,
I want to be taken to the login page automatically after I register,
So that I don't have to find and click a login link to continue.

**Acceptance Criteria:**

**Given** I have just registered successfully,
**When** the registration success state renders,
**Then** a brief confirmation is shown and the app **automatically navigates to `/login`
after ~5 seconds** without requiring a manual click.

**Given** the pending redirect,
**When** the success state is shown,
**Then** the user is told what will happen (e.g. "Registration successful — redirecting to
login…"), and the existing manual login link remains available so an impatient user can go
immediately.

**Given** I leave the page before the timer fires (I click the login link or navigate away),
**When** the component unmounts,
**Then** the pending timer is cleared so no navigation or state update happens after unmount
(no stray redirect, no memory-leak warning).

**Given** the behavior,
**When** implemented,
**Then** it lives in the registration page/route (`RegisterPage`) using react-router
navigation and a cleaned-up timer, and is covered by a test (fake timers assert the redirect
fires after the delay and is cancelled on unmount).

<!-- Epic 10 reopened: Story 10.4 autofocuses the login email field on mount so a user
     auto-redirected from registration (Story 10.3) can start typing immediately.
     Frontend-only; a single-field change on LoginPage. -->

### Story 10.4: Autofocus the Email Field on the Login Page

As a user arriving at the login page (often auto-redirected from registration),
I want the email field to be focused automatically,
So that I can start typing my credentials immediately without clicking into the field.

**Acceptance Criteria:**

**Given** the login page renders its form,
**When** it mounts,
**Then** the **email** input receives focus automatically, so a user redirected from registration
(Story 10.3) can type right away.

**Given** the existing already-authenticated short-circuit (`<Navigate>` in `LoginPage`),
**When** a signed-in visitor is redirected away,
**Then** focus is applied only when the form is actually shown, and it does not steal focus on a
mid-typing re-render.

**Given** the behavior,
**When** implemented,
**Then** it lives in `LoginPage` (e.g. the email `TextField`'s `autoFocus`) and is covered by a test
asserting the email input is the focused element after render.

<!-- Epic 10 reopened (bugfix): Story 10.5 fixes the account menu, which shows the ORG name instead
     of the logged-in user. Root cause: Layout.tsx:115-119 renders activeOrg.name, and AuthProvider
     calls getMe() (line 37) but DISCARDS the user — AuthValue never exposes it. Fix stores + exposes
     the current user and shows user.email. Extends the same auth/me + AuthProvider surface as Story
     2.12 (is_global_admin) — coordinate so both land together. -->

### Story 10.5: Account Menu Shows the Logged-In User, Not the Org (Bugfix)

As a signed-in user,
I want the account/profile menu to show my own identity,
So that I can confirm which account I'm logged in as instead of seeing the org name where my name
should be.

**Context (bug):** The account menu (the `AccountIcon` menu in the app bar) shows the **org** name,
not the user. Root cause (verified): `Layout.tsx:115-119` renders `activeOrg.name` in the menu, and
`AuthProvider.tsx` calls `getMe()` (line 37) purely to establish auth but **discards** the returned
user — the context value (`AuthValue`) never exposes it, so the menu has nothing else to show. There
is also no identity displayed at all for a zero-org user (the `activeOrg &&` block collapses).

**Acceptance Criteria:**

**Given** `AuthProvider` already calls `getMe()` to establish auth,
**When** it resolves,
**Then** the provider **stores** the current `user` (`{id, email}`) and **exposes** it via `useAuth`
(a new `user` field on `AuthValue`), instead of discarding the `getMe()` result.

**Given** the account menu in `Layout`,
**When** it renders for a signed-in user,
**Then** it shows the logged-in **user's email** (`user.email`) as the primary identity; the active
org may remain as a **secondary** context line if desired, but the user identity is what the menu
leads with.

**Given** a signed-in user with **zero** orgs,
**When** the account menu renders,
**Then** it still shows the user's email (identity does not depend on having an active org, Story 2.6).

**Given** the fix,
**When** implemented,
**Then** it extends the same `auth/me` + `AuthProvider` surface as Story 2.12's `is_global_admin`
(coordinate so both signals land on `AuthValue` together), and a test asserts the account menu shows
the logged-in user's email.

<!-- Epic 10 reopened (bugfix): Story 10.6 — pressing Enter on the login screen doesn't submit the
     form (user must click the button). LoginPage LOOKS correct (Paper component="form" onSubmit +
     Button type="submit"), so the story first REPRODUCES via a test simulating Enter, then fixes
     whatever it reveals. Frontend-only. -->

### Story 10.6: Login Form Submits on Enter (Bugfix)

As a user on the login screen,
I want to press Enter in a field to submit the form,
So that I can log in with the keyboard instead of having to click the button.

**Context (bug):** Pressing **Enter** while focused in the email or password field does **not** submit
the login form — the user must click "Log in". `LoginPage.tsx` *looks* correct: a
`<Paper component="form" onSubmit={handleSubmit}>` wrapping the fields with a `<Button type="submit">`
(`LoginPage.tsx:49-77`), which should give implicit form submission. Because the structure appears
right, this story is **test-first**: reproduce the failure before changing code.

**Acceptance Criteria:**

**Given** the reported bug,
**When** work starts,
**Then** a **failing test is written first** that simulates pressing **Enter** in the email (or
password) field and asserts the form submits (`login` is called / `handleSubmit` runs) — reproducing
the bug before any fix.

**Given** the reproduction,
**When** the root cause is identified,
**Then** the fix makes implicit submission work with the MUI `Paper component="form"` structure
(verify the rendered element is a real `<form>` and Enter triggers `onSubmit`); the change stays
minimal and does not regress the existing click-to-submit path.

**Given** the fix,
**When** implemented,
**Then** pressing **Enter** in a login field submits the form, and the test that reproduced the bug now
passes (both Enter-to-submit and click-to-submit are covered).

<!-- Epic 10 reopened (cleanup): 10.7 removes the redundant /dashboard page (a vestigial stub
     superseded by /history's jobs table; not in the nav, duplicated the org switcher + logout) and
     lands post-login on the index page (/) instead. -->

### Story 10.7: Remove the Redundant /dashboard Page; Land Login on the Index Page

As a user,
I want a single, useful home after login instead of an empty placeholder,
So that I'm not dropped on a redundant page that duplicates the shell's controls.

**Context:** `/dashboard` (`DashboardPage`) is a leftover scaffolding stub — not linked in the nav, it
renders a duplicate org switcher + "Log out" (already in the app shell) plus an empty "Your SBOM jobs will
appear here." The real jobs dashboard is `/history` (Stories 6.1–6.3). Login currently defaults to
`/dashboard` (`DEFAULT_AFTER_LOGIN`), dropping users on the empty stub.

**Acceptance Criteria:**

**Given** the redundant page,
**When** the change lands,
**Then** `DashboardPage` and its `/dashboard` route are removed and no references remain (`tsc`/grep clean).

**Given** a successful login with no intended destination,
**When** it completes,
**Then** the user lands on the **index page** (`/`) — `DEFAULT_AFTER_LOGIN = '/'` — while a preserved
`from` destination (a `ProtectedRoute` redirect, Story 10.2) still wins.

**Given** the change,
**When** complete,
**Then** the login round-trip and default-fallback tests pass against `/`, and `pixi run ci` is green.

<!-- Epic 10 (follow-up): 10.8 adds a Home item to the side nav pointing at the index page (/),
     now that login lands there (10.7) and the index is a real landing page (12.8). -->

### Story 10.8: Add a Home Side-Nav Item

As an authenticated user,
I want a "Home" item at the top of the side navigation,
So that I can return to the index/landing page without relying on the brand mark.

**Acceptance Criteria:**

**Given** the authenticated side navigation,
**When** it renders,
**Then** a **Home** entry (→ `/`) is the first item for everyone; the order is **Home, Upload, History,
Members, API Keys, Organization** (Members and Organization stay admin-gated; non-admins see Home, Upload,
History, API Keys).

**Given** `/` is a prefix of every route,
**When** the Home link's active state is computed,
**Then** it uses react-router's `end` prop so Home is highlighted **only** on the index page, and the
other items still highlight on their own routes.

**Given** the change,
**When** complete,
**Then** tests cover the order (admin + non-admin) and the active-only-on-`/` behavior, and `pixi run ci`
is green.

---

## Epic 11: Project Documentation

The project has code and a BMad planning trail but **no reader-facing documentation** —
no user guide, no developer/contributor docs, a thin README, and no published docs
site. This epic documents the whole project in **markdown**, published to **GitHub
Pages** via **MkDocs Material** (installed into the pixi umbrella from conda-forge, so
docs build the same way everything else does). The docs cover both audiences: end
users (register → upload → read reports → export) and developers/contributors
(architecture, local setup, the SBOM pipeline, the REST API, how to contribute).

**Toolchain (decided):** MkDocs Material for the site (markdown-native), with
`mkdocstrings[python]` auto-rendering the backend's Google-style docstrings into a code
reference. Content lives under `docs/`; `mkdocs.yml` defines the nav; a `docs.yml`
workflow deploys to Pages. New dev deps (`mkdocs-material`, `mkdocstrings-python`) are
flagged in the stories that add them. Root-level meta files (README, CONTRIBUTING,
CODE_OF_CONDUCT, SECURITY) stay at the repo root (GitHub renders them there) and are
also surfaced in the site nav where useful.

**Sequencing:** Story 11.1 (site scaffold) is the foundation — it establishes
`docs/`, `mkdocs.yml`, the pixi tasks, and the Pages workflow. The content stories
(11.2–11.5) each add pages and nav entries to `mkdocs.yml`, so they build on 11.1 and
touch a shared file (best done in sequence or with careful nav coordination). Stories
11.6 (meta files) and 11.7 (README) are largely independent of `mkdocs.yml`.

**External prerequisite (operator):** enable GitHub Pages with **source = GitHub
Actions** in repo settings so the `docs.yml` deploy can publish (flagged in 11.1).

- FR-DOC1: A MkDocs Material documentation site is scaffolded, buildable/serveable via
  pixi tasks, and auto-deployed to GitHub Pages on push to `main`.
- FR-DOC2: An end-user **User Guide** covers the full user journey (accounts/orgs,
  uploading manifests, reading each report tab, exporting, downloading the SBOM, job
  history, API keys).
- FR-DOC3: Task-oriented **How-To guides** answer specific "how do I…" questions.
- FR-DOC4: **Developer documentation** covers architecture, local setup, the SBOM
  pipeline, data model, testing, and an auto-generated backend code reference.
- FR-DOC5: A **REST API reference** documents the endpoints (auth, orgs, jobs,
  reports, artifacts, API keys).
- FR-DOC6: **Contribution & project meta-docs** exist: `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`, and issue/PR templates.
- FR-DOC7: The **README** is rewritten as a proper project front page (overview,
  badges, quick start, screenshots, links to the docs site, license).
- FR-DOC8: The app's top navigation exposes quick-access icon links to the **source
  repository** and the **published documentation site**.
- FR-DOC9: The backend serves an **OpenAPI schema** and interactive **Swagger UI** at
  standard endpoints, generated from the live DRF API.
- FR-DOC10: The documentation site is rebuilt and republished as part of the release
  workflow, so a cut release always refreshes the published docs.

### Story 11.1: Documentation Site Scaffold & GitHub Pages Deployment

As a maintainer,
I want a MkDocs Material site wired into pixi and auto-deployed to GitHub Pages,
So that all subsequent documentation has a home that publishes automatically.

**Acceptance Criteria:**

**Given** the pixi umbrella toolchain,
**When** the docs site is scaffolded,
**Then** `mkdocs-material` (and `mkdocstrings-python`, used by Story 11.4) are added as
dev dependencies from conda-forge (**new dev deps — flagged**), a `mkdocs.yml`
configures the Material theme (navigation, search, light/dark palette toggle, repo
link), and a `docs/index.md` landing page exists (FR-DOC1).

**Given** local docs work,
**When** tasks are added,
**Then** `pixi run docs-serve` (live-reload preview) and `pixi run docs-build`
(`mkdocs build --strict`, so broken links/nav fail the build) are defined, and
`docs-build` is runnable in CI.

**Given** pushes to `main`,
**When** docs change,
**Then** a `.github/workflows/docs.yml` builds the site and deploys it to GitHub Pages
using the Pages deploy actions (`actions/configure-pages`, `upload-pages-artifact`,
`deploy-pages`) with the correct `pages: write` / `id-token: write` permissions.

**Given** external setup,
**When** implemented,
**Then** the story documents the one-time operator step — enabling GitHub Pages with
**source = GitHub Actions** — and `mkdocs build --strict` is wired so `pixi run ci`
(or a docs check) stays green.

**Given** the initial nav,
**When** created,
**Then** it establishes the top-level sections (Home, User Guide, How-To, Developer,
API Reference, Contributing) as placeholders the content stories fill in.

### Story 11.2: User Guide

As an end user,
I want a guide that walks through using the app,
So that I can register, generate an SBOM, and understand the results without help.

**Acceptance Criteria:**

**Given** the User Guide section,
**When** authored,
**Then** it covers the full journey in markdown pages: creating an account and
organization, logging in and switching orgs, uploading a manifest (supported formats),
submitting a job and watching progress, and reading the Results page (FR-DOC2).

**Given** the reports,
**When** documented,
**Then** each Results tab is explained — Overview, Vulnerabilities, Licenses,
Dependency Graph (direct vs. transitive), Version Currency (incl. LTS and
PyPI/conda-forge latest), and the in-app SBOM viewer — with what each column/badge
means.

**Given** outputs,
**When** documented,
**Then** exporting reports to Excel, downloading the SBOM document, the Job History
dashboard, and API key management are each covered.

**Given** clarity,
**When** authored,
**Then** screenshots (or annotated placeholders) illustrate the key screens, and pages
are added to the `mkdocs.yml` nav under **User Guide**.

### Story 11.3: How-To Guides

As a user,
I want short task-focused how-to pages,
So that I can quickly accomplish a specific goal without reading the whole guide.

**Acceptance Criteria:**

**Given** the How-To section,
**When** authored,
**Then** it provides concise, task-oriented recipes (FR-DOC3), including at least:
"Generate an SBOM from a `requirements.txt` / `pyproject.toml` / lockfile",
"Interpret the vulnerability report", "Check license compliance", "See which
dependencies are outdated", "Export a report to Excel", "Create and use an API key",
and "Invite a member / switch organizations".

**Given** each how-to,
**When** written,
**Then** it is a focused, numbered-steps page (goal → steps → result), cross-linked to
the relevant User Guide section, and added to the `mkdocs.yml` nav under **How-To**.

### Story 11.4: Developer Documentation

As a contributor,
I want developer documentation of the architecture and codebase,
So that I can set up locally and understand how the system fits together.

**Acceptance Criteria:**

**Given** the Developer section,
**When** authored,
**Then** it covers: an architecture overview (Django/DRF backend, React/Vite SPA,
Celery workers, MinIO, Postgres/Redis, the pixi umbrella), local development setup
(`pixi install`, Docker Compose, running the stack), the project layout, and the
testing model (unit vs. integration, `pixi run ci`) (FR-DOC4).

**Given** the SBOM pipeline,
**When** documented,
**Then** the phased Celery pipeline (generation → enrichment phases → finalize) and the
key data models (jobs, SBOM artifacts, analysis reports) are explained, drawing on the
BMad architecture spine where useful.

**Given** the backend's Google-style docstrings,
**When** the code reference is set up,
**Then** `mkdocstrings[python]` auto-renders an API/code reference for the backend
package into the site (markdown pages with `:::` handlers), so docstrings surface in
the docs.

**Given** navigation,
**When** complete,
**Then** the developer pages are added to the `mkdocs.yml` nav under **Developer**.

### Story 11.5: REST API Reference

As a developer integrating with the app,
I want the HTTP API documented,
So that I can call the endpoints without reading the source.

**Acceptance Criteria:**

**Given** the DRF API,
**When** documented,
**Then** an API Reference section documents the endpoints grouped by area — auth/session,
organizations & membership, API keys, job submission & status, reports
(vulnerabilities, licenses, graph, versions), artifacts/SBOM download — with method,
path, auth requirements, and request/response shape (FR-DOC5).

**Given** "markdown where possible" and accuracy,
**When** implemented,
**Then** the reference is authored in markdown; if an OpenAPI schema is generated
(e.g. via drf-spectacular) it may be surfaced/embedded, but a generated schema tool is
**optional** and any new dependency is flagged and confirmed before adding.

**Given** navigation,
**When** complete,
**Then** the API pages are added to the `mkdocs.yml` nav under **API Reference**.

### Story 11.6: Contribution & Project Meta-Documentation

As a maintainer,
I want standard contribution and community health files,
So that contributors know how to work with the project and report issues securely.

**Acceptance Criteria:**

**Given** the repo root,
**When** the meta-docs are added,
**Then** `CONTRIBUTING.md` documents the workflow (branch naming, Conventional Commits,
the pixi tasks, `pixi run ci` gate, tests-required, PR process), `CODE_OF_CONDUCT.md`
(e.g. Contributor Covenant) and `SECURITY.md` (private vulnerability reporting) exist
(FR-DOC6).

**Given** GitHub's templates,
**When** added,
**Then** `.github/ISSUE_TEMPLATE/` (bug report + feature request) and a
`PULL_REQUEST_TEMPLATE.md` are provided, consistent with the label automation
(Story 9.6) and commit conventions.

**Given** the docs site,
**When** complete,
**Then** `CONTRIBUTING.md` is surfaced in the site nav under **Contributing** (via
include or a short pointer page) so it appears in both places without duplication.

### Story 11.7: README Overhaul

As a visitor to the repository,
I want a README that explains the project at a glance,
So that I understand what it does and where to go next.

**Acceptance Criteria:**

**Given** the current thin README,
**When** rewritten,
**Then** it is a proper project front page: name + one-line description, a status-badge
row (see below), a short overview of what the tool does, a screenshot or two, a Quick
Start (`pixi install` → run the stack), a features summary, and prominent links to the
published docs site and to CONTRIBUTING (FR-DOC7).

**Given** the reference badge style (millsks/conventional-commit-hook) but that this
app is **not published to any package index** (releases only — no PyPI/conda-forge),
**When** the badge row is authored,
**Then** it includes at minimum: **CI** status (the Epic 9 `ci.yml` Actions badge),
**Codecov** coverage, **latest GitHub Release** (`img.shields.io/github/v/release/...`,
replacing the reference's PyPI/conda version badges), **supported Python versions** (a
*static* shields badge reflecting the CI matrix — not the `pypi/pyversions` source,
which requires publication), and **License** — and it **explicitly omits** any
PyPI-version or conda-forge-version badge.

**Given** the request to surface anything else useful to a repo visitor,
**When** the badge row is finalized,
**Then** it also includes the beneficial stack/health badges that fit this project,
each linking to its target — e.g. **docs site** (GitHub Pages, once live from Story
11.1), **SonarCloud** quality gate (Story 9.2), **pre-commit**, **Ruff** (formatter/
linter), **Conventional Commits**, **code style / typed (mypy)**, and repo-signal
badges such as **last commit**, **open issues**, or **PRs welcome** — the implementer
picks the subset that reads well and avoids badge clutter (aim for a tidy one/two-row
row, not an exhaustive wall).

**Given** the other documentation,
**When** the README is written,
**Then** it links to (rather than duplicates) the User Guide, Developer docs, and API
reference, and includes the License section.

### Story 11.8: Repository & Documentation Links in the App Header

As a user,
I want quick links to the source repository and the documentation from the app,
So that I can reach the code and the docs without hunting for URLs.

**Acceptance Criteria:**

**Given** the app's top navigation/header (the Epic 10 shell),
**When** it renders,
**Then** it shows two icon links in the header, on every page and in both auth states:
a **GitHub icon** linking to the source repository, and a **documentation icon** (e.g.
a book/article icon) linking to the published documentation site (FR-DOC8).

**Given** the links point off-site,
**When** activated,
**Then** each opens in a new tab (`target="_blank"` + `rel="noopener noreferrer"`) and
carries an accessible label/tooltip ("GitHub repository", "Documentation").

**Given** the target URLs must not be hard-coded ad hoc,
**When** implemented,
**Then** the repo URL and docs-site URL are sourced from a single config constant (or
Vite env var), with the docs URL matching the GitHub Pages site from Story 11.1
(`https://millsks.github.io/django-python-generate-sbom/`).

**Given** icons are needed,
**When** implemented,
**Then** `@mui/icons-material` is used for the icons (the same **user-approved** dep
introduced in Epic 12 Story 12.2 — if 11.8 lands first it adds the dependency, which
12.2 then builds on), and the icon buttons sit consistently in the header alongside the
theme toggle / user menu without disrupting the existing nav, org switcher, or logout.

**Given** the change touches the shell,
**When** implemented,
**Then** a test covers that both links render with the correct `href`, `target`, and
accessible label.

### Story 11.9: OpenAPI Schema & Swagger UI Endpoint

As a developer integrating with the API,
I want interactive Swagger/OpenAPI docs served by the app at a standard endpoint,
So that I can explore and try the REST API live without reading source or hand-written docs.

**Acceptance Criteria:**

**Given** the DRF API,
**When** OpenAPI generation is added,
**Then** `drf-spectacular` (a **new dependency — flagged**, user-requested) generates an
OpenAPI 3 schema from the live viewsets/serializers, served at a standard **schema
endpoint** (e.g. `/api/schema/`) (FR-DOC9).

**Given** the schema,
**When** the docs UI is wired,
**Then** interactive **Swagger UI** is served at a standard endpoint (e.g.
`/api/docs/`), and ReDoc (e.g. `/api/redoc/`) may also be exposed; the assets are
self-hosted (e.g. `drf-spectacular-sidecar`) so the UI works without external CDNs.

**Given** the app's auth,
**When** the schema is generated,
**Then** it reflects the real authentication schemes (session + API key), groups
endpoints with sensible tags, and `SPECTACULAR_SETTINGS` sets the title, description,
and version; `DEFAULT_SCHEMA_CLASS` points at drf-spectacular's `AutoSchema`.

**Given** exposure of the endpoints,
**When** configured,
**Then** access is deliberate — the docs/schema endpoints are available in development
and their availability in production is configurable (documented) rather than
accidentally always-public.

**Given** the rest of the documentation,
**When** implemented,
**Then** the Story 11.5 API reference and the docs site link to the live Swagger UI
(and the schema may feed the 11.5 reference), and a test asserts the schema and
Swagger-UI endpoints return 200 with a valid schema.

### Story 11.10: Publish Documentation on Release

As a maintainer,
I want the docs rebuilt and republished when a release is cut,
So that the published documentation always reflects the latest release, not just the last docs edit.

**Acceptance Criteria:**

**Given** the release workflow (Story 9.3 `release.yml`),
**When** a release is successfully cut,
**Then** the documentation site is rebuilt and republished to GitHub Pages as part of
that run (FR-DOC10).

**Given** the docs deploy already exists (Story 11.1 `docs.yml`),
**When** the release publishes docs,
**Then** it **reuses** that build/deploy mechanism rather than duplicating it — e.g.
refactor the docs deploy into a reusable `workflow_call` job that both `docs.yml`
(on-push) and `release.yml` (on-release) invoke, or have the release trigger it — so
the mkdocs build + Pages deploy live in one place.

**Given** GitHub Pages allows a single concurrent deployment,
**When** an on-push docs deploy and an on-release docs deploy could overlap,
**Then** a Pages **concurrency group** serializes them so a release publish and a
docs-change publish don't collide or cancel each other destructively.

**Given** the release may no-op (no changes since the last tag),
**When** the scheduled release run skips,
**Then** the docs publish behaves sensibly (either also skips or republishes the
current site) without failing the workflow.

**Given** the operator prerequisite from Story 11.1,
**When** the release publishes docs,
**Then** it relies on the same GitHub Pages setup (Source = GitHub Actions) and App
token/permissions already configured — no new external secret beyond those from
Stories 11.1 and 9.3.

<!-- Epic 11 reopened (documentation reconciliation). The Epic 2 org-membership rework
     (zero-org users, create-org UI, add-existing-member-by-email, the global-admin ADMIN
     org, and the new auth/me endpoint) makes parts of the Epic 11 docs out of date.
     Stories 11.11-11.14 review and update the documentation to match the shipped system.
     PREREQUISITE: these are implemented AFTER Epic 2 is done, so the docs reflect the
     final behavior (they are contexted into story files just-in-time at that point).
     11.11-11.13 are audience-scoped and largely independent (different files); 11.14 is a
     cross-cutting sweep run last. Covers the existing FR-DOC2/3/4/5/7/9. -->

### Story 11.11: User-Facing Documentation Reconciliation (Org Membership)

As an end user,
I want the User Guide and How-To guides to match how accounts and organizations actually work,
So that the instructions I follow don't lead me into errors or dead ends.

**Acceptance Criteria:**

**Given** Epic 2 changed registration so new users start with **zero** organizations,
**When** `docs/user-guide/accounts-and-organizations.md` is reviewed,
**Then** it reflects: a newly registered user has no org and is shown a "create one or ask
an admin to add you" state (not a personal org), how to **create an organization** from the
UI, switching orgs, and that platform (global) admins oversee all orgs (FR-DOC2).

**Given** Epic 2 changed member management to **add an existing user by email** (no more
temp-password auto-create) and defined membership edge cases,
**When** `docs/how-to/manage-organization.md` ("Invite a member / switch organizations") is
reviewed,
**Then** it documents adding a member by their registered email (and the "no such user"
outcome), removing members, the last-admin rule, and create/switch org — with no references
to temporary passwords or auto-created accounts (FR-DOC3).

**Given** the reconciliation,
**When** complete,
**Then** any stale screenshots or wording in these pages are updated, and `pixi run
docs-build` (`mkdocs build --strict`) stays green.

### Story 11.12: API Reference & OpenAPI/Swagger Reconciliation

As an API consumer,
I want the REST API reference and the generated OpenAPI/Swagger to match the live endpoints,
So that I can integrate against accurate request/response contracts.

**Acceptance Criteria:**

**Given** Epic 2 added `GET /api/v1/auth/me/` and changed `POST /auth/register/` to return
`org: null` (zero-org registration),
**When** `docs/api/authentication.md` is reviewed,
**Then** it documents the new `auth/me` identity endpoint (auth required, returns the current
user) and the updated register response, alongside login/logout (FR-DOC5).

**Given** Epic 2 changed add-member to an email-only payload (dropping `temp_password`) and
added create-org / global-admin provisioning,
**When** `docs/api/organizations.md` is reviewed,
**Then** the members endpoint request/response, the create-org endpoint, and the global-admin
behavior are accurate.

**Given** the backend serves a generated OpenAPI schema + Swagger UI (Story 11.9),
**When** the API changed,
**Then** the generated schema reflects the new/changed endpoints (regenerate any committed
schema artifact if present), and the docs match what Swagger renders (FR-DOC9). `mkdocs build
--strict` stays green.

### Story 11.13: Developer Documentation Reconciliation (Global-Admin Model)

As a developer/contributor,
I want the developer docs to describe the org-membership and global-admin model as built,
So that I can reason about permissions and set up an environment correctly.

**Acceptance Criteria:**

**Given** Epic 2 introduced the system **ADMIN** org (`Org.is_admin_org`) whose members are
global admins provisioned as admins of all orgs,
**When** `docs/developer/architecture.md` is reviewed,
**Then** it documents the global-admin tier as a deliberate cross-org superuser tier, how
permission checks treat global admins as org admins everywhere, and the zero-org/identity
decoupling (auth is independent of org membership) (FR-DOC4).

**Given** the data model changed (`is_admin_org` flag; users may have zero memberships),
**When** `docs/developer/data-model.md` is reviewed,
**Then** the `Org`/`OrgMembership`/`User` descriptions and any diagram reflect the flag, the
zero-org state, and global-admin memberships.

**Given** the initial superuser is now seeded into the ADMIN org (via the `bootstrap_admin_org`
management command / superuser hook rather than an auto-created personal org),
**When** `docs/developer/setup.md` is reviewed,
**Then** the first-run/superuser bootstrap steps are accurate. `mkdocs build --strict` stays green.

### Story 11.14: Cross-Cutting Documentation Audit & Refresh

As a maintainer,
I want a final sweep of all documentation for drift beyond the org-membership changes,
So that the published docs and README are trustworthy after the recent epics.

**Acceptance Criteria:**

**Given** the README is the project front page (Story 11.7),
**When** it is reviewed,
**Then** any personal-org / registration wording is corrected and the overview, quick start,
and screenshots reflect the current app (FR-DOC7).

**Given** recent UI work (Epic 12 visual polish, Epic 10 navigation) may have dated
screenshots or descriptions across the docs,
**When** the full `docs/` tree is audited,
**Then** stale screenshots, navigation descriptions, and prose are refreshed, and the
auto-generated code reference (mkdocstrings) still renders.

**Given** the docs site enforces link integrity,
**When** the audit completes,
**Then** `pixi run docs-build` (`mkdocs build --strict`) passes with no broken links/nav, and
anything found but out of scope for 11.11-11.13 is fixed here or explicitly noted.

<!-- Epic 11 reopened AGAIN (documentation reconciliation, 2nd pass). The first pass (11.11-11.14)
     only covered the INITIAL Epic 2 org-membership work. A lot merged since — through Story 13.1
     (global-admin management screen): the admin tier (per-org admin vs. global admin), create-org
     gating to global admins, add-by-email + create-new-user, promote (not transfer) + demote,
     admin-route + API authorization, the global-admin management screen, and the version-currency
     PyPI-Latest / Excel-divergence / conda-forge python-<name> changes (8.22-8.24). Stories
     11.15-11.18 reconcile the published docs to this state. PREREQUISITE: implement against the
     then-current merged state (at minimum through 13.1); recommended after Stories 2.18-2.20 merge
     so the org-access refinements land in one pass. 11.15-11.17 are audience-scoped; 11.18 is the
     cross-cutting sweep run last. Covers FR-DOC2/3/4/5/7/9. -->

### Story 11.15: User-Facing Documentation Reconciliation (Admin Tier, 2nd Pass)

As an end user,
I want the User Guide and How-To guides to reflect the current roles, admin actions, and zero-org experience,
So that the instructions I follow match what the app actually does now.

**Acceptance Criteria:**

**Given** the system now has three role tiers (member / org-admin / global-admin) and a refined zero-org
experience (Stories 2.8, 2.12, 2.18, 2.19),
**When** `docs/user-guide/accounts-and-organizations.md` is reviewed,
**Then** it documents the member/org-admin/global-admin roles, the zero-org experience (no org on
registration → restricted to home until an admin adds them), org switching (switcher hidden for a single
org), and that creating an organization is restricted to global admins (the ADMIN org hidden from the
switcher) (FR-DOC2).

**Given** the admin toolkit grew (add-existing-by-email, create-new-user, promote, demote, remove),
**When** `docs/how-to/manage-organization.md` is reviewed,
**Then** it documents adding a member by registered email (+ "no such user"), creating a new user account
(Story 2.10), promoting a member to admin (not "transfer" — Story 2.16), demoting admin→member (Story 2.20),
and removing a member with the last-admin rule — with no "transfer admin" wording (FR-DOC3).

**Given** the global-admin management screen shipped (Story 13.1),
**When** the user-facing docs are updated,
**Then** they describe the global-admin management flow (global-admin-only visibility; list current global
admins; grant by email; revoke = remove-from-ADMIN + demote-everywhere, with the last-global-admin guard),
stale screenshots/wording are updated, and `pixi run docs-build` (`mkdocs build --strict`) stays green.

### Story 11.16: API Reference & OpenAPI Reconciliation (Admin Tier, 2nd Pass)

As an API consumer,
I want the REST API reference and the generated OpenAPI/Swagger to match all the current endpoints,
So that I can integrate against accurate contracts for the admin and global-admin surfaces.

**Acceptance Criteria:**

**Given** `GET /api/v1/auth/me/` now returns `is_admin` and `is_global_admin` (Stories 2.6, 2.12),
**When** `docs/api/authentication.md` is reviewed,
**Then** it documents `auth/me` returning the current user with both flags, alongside register/login/logout
(FR-DOC5).

**Given** the membership surface grew (create-new-user, promote-admin) and create-org is global-admin-gated,
**When** `docs/api/organizations.md` is reviewed,
**Then** it documents `POST /orgs/members/` (add-existing by email), `POST /orgs/members/create-user/`
(Story 2.10), `POST /orgs/promote-admin/` (Story 2.16), member remove, and `POST /orgs/create/`
(global-admin-gated — Story 2.12), each with request/response shapes and error codes.

**Given** the global-admin management endpoints exist (Story 13.1) and the backend serves OpenAPI/Swagger
(Story 11.9),
**When** the API changed,
**Then** a global-admin section documents `GET`/`POST`(grant-by-email)/`DELETE` on `admin/global-admins/`
(revoke = remove-from-ADMIN + demote-everywhere; last-global-admin guard; 403 for non-global-admins), the
generated schema reflects all new/changed endpoints (regenerate any committed artifact), and the docs match
what Swagger renders (FR-DOC9). `mkdocs build --strict` stays green.

### Story 11.17: Developer/Architecture Documentation Reconciliation (Admin Tier, 2nd Pass)

As a developer/contributor,
I want the developer docs to describe the org/admin/auth model, authorization, and the version-currency
changes as built,
So that I can reason about permissions and the codebase correctly.

**Acceptance Criteria:**

**Given** the system has per-org admin vs. a global-admin tier, admin-route + API authorization, and
promote/demote (Stories 2.8, 2.16, 2.17, 2.20),
**When** `docs/developer/architecture.md` is reviewed,
**Then** it documents the org-membership model, per-org admin vs. global admin (the ADMIN org + cross-org
provisioning), the admin-route + API-authorization pattern (enforced at both route and API), promote/demote,
and zero-org/identity decoupling (`auth/me`) (FR-DOC4).

**Given** the data model changed (`is_admin_org`, zero-membership users, global-admin memberships, roles)
and superuser seeding is env-driven (Story 2.13),
**When** `docs/developer/data-model.md` and `docs/developer/setup.md` are reviewed,
**Then** the model docs reflect the flag/zero-org state/global-admin memberships (refresh any diagram), and
setup documents env-driven `seed_superuser` bootstrap into the ADMIN org (not a personal org).

**Given** the version-currency work (PyPI-Latest column + Excel red divergence, conda-forge `python-<name>`
disambiguation — Stories 8.22-8.24),
**When** the developer docs are reviewed,
**Then** those changes are documented, the mkdocstrings code reference still renders the new/updated services
(`grant_global_admin`, `revoke_global_admin`, `promote_member_to_admin`), and `mkdocs build --strict` stays
green.

### Story 11.18: Cross-Cutting Documentation Sweep (2nd Pass)

As a maintainer,
I want a final sweep of the README and full docs tree for drift since the last pass,
So that the published docs and README are trustworthy after the admin-tier, landing-page, and nav changes.

**Acceptance Criteria:**

**Given** the README is the project front page (Story 11.7),
**When** it is reviewed,
**Then** it reflects the current app — role model, zero-org registration, create-org gating, the landing page
(Story 12.8), and current nav (login→index, home nav item, account-menu user, dashboard removed — Epic 10) —
and any stale personal-org / transfer-admin / registration wording is corrected (FR-DOC7).

**Given** recent work (the landing page 12.8, nav changes in Epic 10, admin screens, version-currency
8.22-8.24) may have dated screenshots or prose across the docs,
**When** the full `docs/` tree is audited,
**Then** stale screenshots, navigation descriptions, and prose are refreshed, and the auto-generated code
reference (mkdocstrings) still renders.

**Given** the docs site enforces link integrity,
**When** the audit completes,
**Then** `pixi run docs-build` (`mkdocs build --strict`) passes with no broken links/nav, and anything found
but out of scope for 11.15-11.17 is fixed here or explicitly noted.

<!-- Story 11.19 reconciles the GENERATED OpenAPI schema (what Swagger UI renders), distinct from
     11.16 which reconciles the markdown API reference. User-reported gap: several endpoints render in
     Swagger with no "Try it out" inputs because the hand-rolled APIViews build serializers inside
     .post()/.delete() (opaque to drf-spectacular) or read request.data directly with no serializer at
     all — so the schema emits no requestBody/parameters. This story annotates the views so every
     endpoint exposes its payload fields, path/query params, and response shapes. Keep consistent with
     11.16. PREREQUISITE: implement against the then-current merged state (at minimum through 13.1;
     recommended after 2.18-2.20). Covers FR-DOC9. -->

### Story 11.19: OpenAPI/Swagger Schema Completeness (Request Bodies & Parameters)

As an API consumer using the Swagger UI,
I want every endpoint in the generated OpenAPI schema to declare its request body, path/query parameters, and response shapes,
So that "Try it out" shows input fields for the payload and parameters instead of an empty form.

**Acceptance Criteria:**

**Given** most mutating endpoints are hand-rolled `APIView`s that build a serializer inside `.post()`
(opaque to drf-spectacular) or read `request.data` directly with no serializer (`orgs/switch/`,
`sbom/jobs/artifacts/bulk-delete/`), so their operations emit no `requestBody`,
**When** the generated schema (`/api/schema/`) is regenerated,
**Then** every mutating operation declares a `requestBody` exposing its payload fields — via an attached
`serializer_class` or `@extend_schema(request=…)`, authoring request serializers for the two endpoints that
have none today, and declaring `multipart/form-data` for the file uploads (`manifests/upload/`,
`sbom/generate/`) — so Swagger "Try it out" renders input fields (FR-DOC9).

**Given** parameterized endpoints (`<int:user_id>`, `<str:key_id>`, `<uuid:task_id>`) and the custom query
filters on `GET /sbom/jobs/` (`status`, `format`) are not fully declared,
**When** the schema is regenerated,
**Then** each path parameter is present and typed, and each custom query filter is declared via
`OpenApiParameter`, so Swagger renders the corresponding inputs; and each operation declares accurate
response schemas for its success status (including `201`/`202`/`204`/`303`) and the meaningful `{error, code}`
error shapes.

**Given** the schema must stay complete as the API evolves,
**When** the change lands,
**Then** a unit test generates the OpenAPI schema in-process (no live server, no network) and asserts the
previously-missing endpoints now declare a `requestBody` and/or `parameters` (at minimum `orgs/switch/`,
`sbom/jobs/artifacts/bulk-delete/`, the two multipart uploads, and the `GET /sbom/jobs/` query params),
generating the schema produces no new drf-spectacular warnings for the touched endpoints, and `pixi run ci`
is green including `docs-build`.

### Story 11.20: API Docs (Swagger UI) Link in the App Header — Env-Gated

As a developer using the app,
I want a link to the interactive API docs (Swagger UI) in the header alongside the Documentation and GitHub links,
So that I can jump straight to the live API explorer — but only on deployments where those docs are enabled.

**Acceptance Criteria:**

**Given** the app header (the Epic 10 shell) already shows the Documentation and GitHub icon-links (Story 11.8),
**When** it renders on a deployment where the API docs are enabled,
**Then** it shows a third **API-docs icon-link** — an API/schema icon from `@mui/icons-material`, reusing the
Story 11.8 `ExternalIconLink` pattern — immediately adjacent to those links, opening the Swagger UI at `/api/docs/`
(Story 11.9) in a new tab (`target="_blank"` + `rel="noopener noreferrer"`) with an accessible label/tooltip
("API docs").

**Given** the docs are not always exposed,
**When** the API-docs flag resolves to false or is unset,
**Then** the API-docs link is **completely absent** from the header (not merely hidden/disabled) — no icon,
tooltip, or anchor exists — while the Documentation and GitHub links are unaffected.

**Given** the `/api/docs/` endpoint is already gated behind `settings.API_DOCS_ENABLED` (Story 11.9), returning
404 when off,
**When** the frontend decides whether to show the link,
**Then** it derives that decision from the **same** flag so the link and the endpoint enable together and the
link never points at a 404 — the recommended mechanism is a small **public runtime config endpoint** (surfacing
`API_DOCS_ENABLED` to the SPA) so a Docker deploy can toggle both with one env var without rebuilding the
frontend image (a build-time `VITE_ENABLE_API_DOCS` mirroring the Story 11.8 config pattern is the documented
alternative, with its rebuild/drift trade-off).

**Given** the change touches the shell (and possibly a new endpoint),
**When** implemented,
**Then** a frontend test asserts the link renders with the correct `href`/`target`/`rel`/label when the flag is
true and is absent when false/unset (mocking the flag source), plus a backend test for the config endpoint if one
is added, and `pixi run ci` is green.

---

## Epic 12: UI/UX Visual Design & Professional Polish

The SPA is functional but visually utilitarian — default MUI styling, ad-hoc spacing,
few icons, and no consistent visual identity. This epic makes the application **look
professional**: a deliberate theme (color palette, typography, component defaults),
consistent **Material iconography**, a polished **layout** (refined header, a persistent
side navigation with contextual side information, and a footer), page-level polish
(cards, spacing, empty/loading/error states, responsiveness), and light branding.

Frontend-only. It builds on the existing MUI foundation — `ThemeModeProvider`
(Story 5.7, light/dark) and the `Layout` app shell + auth-aware nav (Epic 10) — and
**refines** them rather than replacing them; existing routes, auth behavior, and the
org switcher/theme toggle stay intact. Accessibility (color contrast, focus states,
`aria` labels on icon-only controls) is a cross-cutting requirement, not a separate
story.

**New dependency (user-approved):** `@mui/icons-material` for Material icons (the user
explicitly requested Material icons since the app already uses MUI). Any other addition
is flagged and confirmed before use.

**Sequencing:** Story 12.1 (theme/design-system foundation) comes first — everything
else consumes its tokens. 12.2 (icons) and 12.3 (layout) build on 12.1; 12.4 (page
polish) applies 12.1–12.3 across the pages; 12.5 (branding) is light and can land last.

- FR-UI1: A centralized, professional MUI theme defines the palette, typography,
  spacing, shape, and component default styling for both light and dark modes.
- FR-UI2: Material icons (`@mui/icons-material`) are used consistently across
  navigation, actions, status indicators, and report tabs — icon-only controls carry
  accessible labels.
- FR-UI3: The application layout is professional and consistent: a refined header/app
  bar, a persistent side navigation (drawer) with contextual side information, a main
  content region, and a footer.
- FR-UI4: Every page applies the design system consistently — cards/sections, spacing,
  and first-class empty, loading (skeletons), and error states — and is responsive
  down to small screens.
- FR-UI5: The app has a light visual identity — app name/logo treatment, favicon, and
  accent usage — that reads as a cohesive product.
- FR-UI6: The UI meets baseline accessibility — sufficient contrast in both themes,
  visible focus, and labels on icon-only controls.
- FR-UI7: The SPA has a proper document title (the product name), replacing the
  placeholder "frontend".
- FR-UI8: The site uses a deliberate favicon (not a scaffold placeholder).

### Story 12.1: Theme & Design System Foundation

As a user,
I want the app to have a deliberate, consistent visual style,
So that it feels like a polished professional product rather than default components.

**Acceptance Criteria:**

**Given** the current default-ish MUI setup,
**When** the theme is established,
**Then** a centralized theme (extending `ThemeModeProvider`) defines a professional
**palette** (primary/secondary/error/warning/info/success + background/surface) for
**both light and dark** modes, a **typography** scale (font family, headings, body,
captions), and **shape/spacing** tokens (FR-UI1).

**Given** the user-supplied brand palette (below) is the source of truth,
**When** the palette is authored,
**Then** the theme derives its tokens from these exact hex values — mapping the brand
red/gold to `primary`/`secondary`, the neutral ramp to background/surface/text/divider
(light and dark), and the accent spectrum to a data-visualization / status scale — and
does **not** substitute default MUI colors for them.

#### Brand Palette (source of truth)

Sampled from the reference image the user provided.

| Role | Hex | Notes |
|---|---|---|
| **Primary** (brand red) | `#D71E28` | Headers, primary actions, brand accents |
| **Secondary** (gold) | `#FFCD41` | Secondary accents, highlights, callouts |
| Gold tints | `#FFDE84`, `#FFF0C8`, `#FFF7E2` | Warm surfaces / hover / selected fills |
| **Accent spectrum** (warm→cool) | `#EB691E` orange · `#D73F26` red-orange · `#C83255` rose · `#AA1E87` magenta · `#823291` purple · `#5A469B` indigo | Sequential/categorical scale for charts, severity, badges |
| Neutrals (dark→light) | `#141414` · `#3B3331` · `#787070` · `#B5ADAD` · `#F4F0ED` · `#FFFFFF` | Text, dividers, surfaces, backgrounds |

Suggested mode mapping: **light** — background `#F4F0ED`/`#FFFFFF`, text `#141414`, dividers `#B5ADAD`; **dark** — background `#141414`/`#3B3331`, text `#F4F0ED`, dividers `#787070`. Design note: the brand red is also the semantic **error** color — pick a distinct error red (or a spectrum tone) so "primary" and "error" remain visually distinguishable, and verify every foreground/background pair meets WCAG AA (some tones — e.g. gold on white — need a darker text pairing).

**Given** repeated component styling,
**When** the theme is authored,
**Then** it sets sensible **component defaults** (e.g. `MuiButton`, `MuiCard`,
`MuiAppBar`, `MuiTable`, `MuiChip`, `MuiTextField`) via `theme.components` so pages
don't restyle ad-hoc, and the existing light/dark toggle (Story 5.7) keeps working.

**Given** accessibility,
**When** colors are chosen,
**Then** text/background contrast meets WCAG AA in both themes and interactive
elements have a visible focus state (FR-UI6).

**Given** the theme is the single source of truth,
**When** implemented,
**Then** hard-coded colors/spacing in existing components are migrated to theme tokens
where practical, and a short developer note documents the palette/typography choices.

### Story 12.2: Material Icons Adoption

As a user,
I want meaningful icons throughout the UI,
So that actions and information are quicker to scan and the app looks finished.

**Acceptance Criteria:**

**Given** the app uses MUI,
**When** icons are adopted,
**Then** `@mui/icons-material` is added as a dependency (**user-approved**) and icons
are applied consistently: navigation items, primary actions (upload, export, download,
delete, add), status/severity indicators (vulnerability severity, currency badges, job
status), and the report tabs (FR-UI2).

**Given** icon-only controls (e.g. theme toggle, overflow menus, close buttons),
**When** rendered,
**Then** each has an accessible label (`aria-label`/tooltip) so it is usable by screen
readers (FR-UI6).

**Given** consistency,
**When** icons are chosen,
**Then** a single icon vocabulary is used for a given concept across the app (the same
icon means the same thing everywhere), and icon sizing/color follows the theme.

### Story 12.3: Application Layout — Header, Footer & Side Navigation

As a user,
I want a professional, consistent page layout,
So that navigation and context are always where I expect them.

**Acceptance Criteria:**

**Given** the Epic 10 app shell,
**When** the layout is refined,
**Then** it presents a polished structure: a refined **header/app bar** (brand, primary
nav, org switcher, theme toggle, user menu), a **persistent side navigation** (drawer,
collapsible/responsive) for the primary destinations with the active item indicated,
a **main content region**, and a **footer** (app name, version, links to docs/repo/
license) (FR-UI3).

**Given** the request for "side information",
**When** the layout is built,
**Then** the side region can surface contextual information (e.g. active org, quick
status, or contextual help) alongside primary navigation, without crowding the content.

**Given** smaller screens,
**When** the layout renders,
**Then** the side navigation collapses to a temporary drawer (hamburger) and the header
adapts, so the layout is usable on mobile widths (FR-UI4).

**Given** the existing behavior,
**When** the shell is refined,
**Then** routes, auth-aware/role-aware nav, the org switcher, theme toggle, and logout
continue to work unchanged (a refinement of Epic 10, not a rewrite).

### Story 12.4: Page-Level Visual Polish & States

As a user,
I want every page to look consistent and handle all states gracefully,
So that the whole app feels cohesive and considered.

**Acceptance Criteria:**

**Given** the design system (12.1–12.3),
**When** each page is polished,
**Then** the pages (Upload/New job, Results tabs, Job History, API Keys, Login/
Register, Org/Members) use consistent **cards/sections, spacing, and headings**, and
tables/lists share a consistent treatment (FR-UI4).

**Given** asynchronous data,
**When** a page loads, is empty, or errors,
**Then** it shows first-class **loading** (skeletons/spinners), **empty**, and
**error** states rather than blank or abrupt UI — reusing shared state components.

**Given** varying viewports,
**When** pages render,
**Then** layouts are **responsive** (usable from mobile to desktop), with no horizontal
overflow of primary content.

### Story 12.5: Branding & Visual Identity

As a visitor,
I want the app to have a recognizable identity,
So that it reads as a real product.

**Acceptance Criteria:**

**Given** the app currently has no distinct identity,
**When** branding is added,
**Then** an app name/logo treatment appears in the header, a **favicon** and page
`<title>` are set, and accent color usage is applied consistently per the theme
(FR-UI5).

**Given** the brand palette defined in Story 12.1 (Brand Palette — source of truth:
red `#D71E28`, gold `#FFCD41`, and the accent/neutral ramps),
**When** the logo/identity is designed,
**Then** it draws from that same palette so the app, README, and docs read as one
cohesive product identity.

**Given** the docs and README (Epic 11),
**When** branding assets exist,
**Then** any logo/screenshots produced here are reusable by the README/docs, keeping
the product identity consistent across the repo and the app.

### Story 12.6: Set the SPA Document Title

As a user,
I want the browser tab to show the product name,
So that the app is identifiable among my open tabs instead of reading "frontend".

**Acceptance Criteria:**

**Given** `frontend/index.html` currently has `<title>frontend</title>` (the Vite
placeholder),
**When** the title is set,
**Then** the base document title is the product name (the same name used in the header
brand / README), so a freshly loaded page shows it in the browser tab (FR-UI7).

**Given** the SPA has multiple routes,
**When** navigating between pages,
**Then** the title may optionally reflect the current page (e.g. `Upload · <App>`)
while always falling back to the product name — a small per-route title helper is
acceptable but the base title fix is the required part.

**Given** consistency with branding,
**When** implemented,
**Then** the title matches the app name established for the header/branding (Story 12.5)
and the `config.ts` app identity, avoiding a second hard-coded name string.

### Story 12.7: Update the Site Favicon

As a user,
I want the browser tab to show a real favicon,
So that the app is recognizable and looks finished, not a scaffold default.

**Acceptance Criteria:**

**Given** `frontend/index.html` currently links a scaffold favicon (`/favicon.svg`),
**When** the favicon is updated,
**Then** it is replaced with the deliberate favicon asset in `frontend/public/`, wired
via the `<link rel="icon">` tag(s) (with appropriate size/format variants), and shows
in the browser tab (FR-UI8).

**Given** the favicon should be license-clean and consistent with the app's iconography,
**When** the asset is chosen,
**Then** it is derived from a **Material Design icon** in `@mui/icons-material` (already
a dependency; Material icons are Apache-2.0 licensed — no trademark concern, unlike the
Python logo), picking an icon apt for an SBOM tool (candidates: `AccountTree` / `Hub`
for the dependency graph, `Inventory2` for a bill of materials, or `Shield` /
`VerifiedUser` for the security angle).

**Given** the chosen icon,
**When** the favicon is produced,
**Then** the icon's SVG is emitted as a static `frontend/public/favicon.svg` colored
with the brand palette (e.g. primary red `#D71E28` on a suitable background), and wired
via `<link rel="icon">` (with size/format variants as needed) so it renders crisply in
the browser tab.

**Given** the favicon and branding,
**When** complete,
**Then** the favicon matches the app's Material icon vocabulary (Story 12.2) and the
app-name/logo treatment (coordinated with Story 12.5, which owns the broader visual
identity; 12.7 owns the favicon specifically).

<!-- Epic 12 reopened: the home page (`/`) was nearly empty (app name + one line). Story 12.8
     builds a real landing page — hero + CTA, feature grid, and a how-it-works section — on the
     12.1 design system, theme-aware and responsive. -->

### Story 12.8: Landing Page (App Home)

As a visitor,
I want the home page to explain what the app does and how to start,
So that I understand the product and can jump straight into generating an SBOM.

**Acceptance Criteria:**

**Given** the `/` route (public, in the app shell),
**When** it renders,
**Then** `HomePage` shows a **hero** — the app name (`APP_NAME`), a headline and short supporting
line, a primary CTA **"Upload a manifest"** linking to `/upload` (anonymous users are routed to login
by `ProtectedRoute`), and a secondary **"Read the docs"** link to `DOCS_URL`.

**Given** the hero,
**When** the page continues,
**Then** a responsive **"What you get"** grid presents the real features (SBOM document, vulnerability
report, license compliance, dependency graph, version currency, Excel export), each an icon (reusing the
`TabIcon`/action-icon vocabulary from Story 12.2) + title + one-line blurb, and a **"How it works"**
section lays out the upload → resolve/analyze → review → export flow.

**Given** the design system (Story 12.1),
**When** complete,
**Then** the page uses MUI theme components and palette colors only (no hard-coded colors), reads well in
both light and dark, is responsive down to mobile, and is covered by a test (headline, the `/upload` CTA,
the docs link, and the feature tiles). `pixi run ci` is green.

---

## Epic 13: Platform Administration

The system has a global-admin tier — members of the distinguished **ADMIN** org (`Org.is_admin_org`,
Story 2.8) who are provisioned as admins of every org. But there is **no UI to manage it**: granting is
backend-only (`POST /api/v1/admin/global-admins/`), and there is no way to list current global admins or
**revoke** the status. This epic adds a global-admin-only management screen. (Distinct from ordinary
org-admin management, which is strictly per-org — Stories 2.3 / 2.7 / 2.16.)

### Story 13.1: Global-Admin Management Screen

As a global admin,
I want a screen to see, grant, and revoke global admins,
So that I can manage the platform's superuser tier without shell or DB access.

**Context:** `services.grant_global_admin` (Story 2.8) exists but is only exposed by a bare grant
endpoint; there is no list, no revoke, and no UI. `is_global_admin` is on `auth/me` (Story 2.12) for
gating, and Story 2.17 introduces the admin-route + API-authorization pattern this screen reuses (gated on
global-admin here). Revoke is new; its semantics were decided with the product owner (below).

**Acceptance Criteria:**

**Given** the caller is a **global admin**,
**When** they open the global-admin screen (a new global-admin-only route + a nav entry shown only when
`isGlobalAdmin`),
**Then** they see the current global admins (the ADMIN-org members, by email). A non-global-admin is
blocked at BOTH the route (redirected) and the API (403) — nav hiding is not the gate (cf. Story 2.17).

**Given** a global admin grants global admin **by email**,
**When** the email matches a registered user,
**Then** that user is granted global admin via `grant_global_admin` (added to the ADMIN org + provisioned
as admin of every org); an unknown email returns a clear error (no auto-create).

**Given** a global admin **revokes** another global admin,
**When** the revoke is confirmed,
**Then** the target is **removed from the ADMIN org AND demoted to `member` in every non-admin org** (the
decided semantics — fully revoke the elevated access; pre-global roles are not tracked, so all their admin
roles drop to member, and an org admin can re-promote them per-org if needed).

**Given** the revoke would remove the **last** global admin,
**When** attempted,
**Then** it is blocked — the ADMIN org must never lose its last member (Story 2.9) — with a clear error. A
global admin may revoke themselves as long as they are not the last.

**Given** the change,
**When** complete,
**Then** backend endpoints exist to **list** and **revoke** global admins (grant exists; extend it to
accept email if needed), all global-admin-gated; the screen (list / grant-by-email / revoke with a
confirm) is covered by tests, and `pixi run ci` is green.

---

## Epic 14: Planning-Artifact Reconciliation

A lot merged since the planning artifacts were last touched — through Story 13.1 (global-admin management
screen). The PRD and architecture artifacts now **contradict the shipped system**: the PRD still describes a
personal org created at registration and an admin "transfer" that no longer exist, and neither the PRD nor
the architecture covers the global-admin tier, org-creation gating, add-by-email/create-user, promote/demote,
admin authorization, or the global-admin management screen. This epic reconciles the **planning artifacts**
(PRD + architecture) to the merged state. (Distinct from Epic 11's reopened stories, which reconcile the
**published docs** — `docs/**` + README.)

**PREREQUISITE:** reconcile against the then-current merged state (at minimum through Story 13.1);
recommended after Stories 2.18-2.20 merge so the org-access refinements land in one pass. Planning artifacts
only — no `docs/**` or code edits.

### Story 14.1: PRD Reconciliation (Org Membership & Global-Admin Tier)

As a product owner,
I want the PRD to describe the account/org/admin model as actually built,
So that the planning trail is trustworthy and no longer contradicts the shipped system.

**Acceptance Criteria:**

**Given** the PRD still describes a personal org created at registration and an admin "transfer" (both
reversed — Stories 2.6, 2.16, 2.20),
**When** `prd.md` is reviewed,
**Then** the superseded items are corrected: the "personal org at registration" narrative and **FR-1.1** →
zero-org registration; **FR-1.5** "transfer admin" → promote/demote (org keeps ≥1 admin); FR-1.2/FR-1.3
reconciled to global-admin-gated create-org and the add-existing-by-email / create-new-user split.

**Given** the PRD has zero coverage of the org-membership + admin model,
**When** new FRs are authored,
**Then** `prd.md` gains FRs covering: zero-org identity decoupling (`auth/me` with `is_admin`/
`is_global_admin`); add-by-email + create-new-user; org-creation gating to global admins; the global-admin
ADMIN-org tier + cross-org provisioning; promote/demote; admin authorization (route + API); and global-admin
management (list / grant-by-email / revoke = remove-from-ADMIN + demote-everywhere, with a last-global-admin
guard).

**Given** the PRD package must stay internally consistent,
**When** the FRs change,
**Then** `addendum.md` (Data Models / app-structure sections) is checked and updated where it references the
old personal-org / transfer-admin model.

### Story 14.2: Architecture Reconciliation (Org/Admin/Auth Model & Diagrams)

As an architect,
I want the architecture artifacts and diagrams to document the org/admin/auth model and the global-admin
tier,
So that the architecture spine reflects the system as built and downstream work stays consistent.

**Acceptance Criteria:**

**Given** the architecture spine has no coverage of the org/admin/auth model,
**When** `ARCHITECTURE-SPINE.md` is reviewed,
**Then** it documents (via an invariant/AD entry and/or the entity-relationship + capability-map sections)
the org-membership model, per-org admin vs. global admin (the ADMIN org, `Org.is_admin_org`, + cross-org
provisioning), admin authorization at both route and API, zero-org/identity decoupling (`auth/me`), and
promote/demote — consistent with AD-2 (OrgScopedModel).

**Given** the solution design and one-pager predate the org/admin model,
**When** they are reviewed,
**Then** `solution-design.md` and `one-pager.md` describe the account/org/admin model and the global-admin
tier (not the old personal-org model), including the new endpoints/flows (`auth/me`, create-org gating,
add-by-email/create-user, promote/demote, global-admin management).

**Given** the diagrams predate the org/admin model,
**When** `architecture-diagrams.html` is reviewed,
**Then** the entity/relationship view includes the ADMIN org / `is_admin_org` / roles / global-admin
memberships and the zero-org state, and the flow diagrams reflect the new endpoints (auth/me,
admin/global-admins, promote-admin, members/create-user).
