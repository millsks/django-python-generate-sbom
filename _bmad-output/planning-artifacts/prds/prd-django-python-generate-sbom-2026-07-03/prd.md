---
title: "django-python-generate-sbom — Product Requirements Document"
status: final
created: 2026-07-03
updated: 2026-07-03
finalized: 2026-07-03
---

# django-python-generate-sbom

## Problem Statement

Python projects carry dozens to thousands of transitive dependencies. When a vulnerability surfaces, a license audit is requested, or a software procurement team asks "what is in this software?", developers have no fast, self-service answer. Existing tools are either CLI-only (unusable from a web service), require the project to be installed locally, or produce raw machine data with no interpretation. There is no open-source web service that accepts a raw Python manifest or lock file and returns a structured SBOM plus human-readable analysis in a single workflow.

## Product Vision

A self-hosted, open-source Django web service that accepts Python dependency manifests, generates production-grade Software Bills of Materials in standard formats (CycloneDX, SPDX), and delivers four analysis reports — vulnerability findings, license obligations, dependency graph, and version currency — through both a web UI and a REST API. Any developer or DevSecOps team can deploy it from a Docker Compose file and start generating SBOMs in minutes.

---

## Users

**Developer (primary)** — uploads their project's manifest or lock file, reviews results, and downloads the SBOM for handoff to a security team or procurement process. Expects fast turnaround (under 2 minutes for most projects) and results they can act on without reading the raw SBOM.

**DevSecOps / security engineer** — runs SBOM generation on multiple projects, consumes results via API for pipeline integration, and monitors vulnerability findings across projects. Values API key access, machine-readable output, and consistent behavior across manifest formats.

**Org admin** — manages team membership and API keys for their organization. Creates the org, invites teammates, and controls which keys are active.

---

## Org and User Model

The service uses a GitHub-style org model:

- A **user** is a person with an account (email + password). A user may belong to multiple orgs.
- An **org** is the tenant boundary. All resources (jobs, artifacts, API keys) belong to an org. Org A cannot see or access Org B's data under any circumstance.
- Within an org, a user is either **admin** (can invite/remove members, manage API keys) or **member** (can submit jobs and view results).
- A user can create their own personal org at registration. Additional orgs require an invitation.

---

## Features

### F1 — Account and Org Management

**FR-1.1** A new user registers with an email address and password. Registration creates a personal org named after the user.

**FR-1.2** A registered user can create additional orgs, becoming the admin of each created org.

**FR-1.3** An org admin can add a new member by creating an account on their behalf: entering the new member's email address and a temporary password. The admin shares these credentials with the new member out-of-band. No email infrastructure is required.

**FR-1.4** An org admin can remove a member from the org. Removed members lose access to all org resources immediately.

**FR-1.5** An org admin can transfer admin privileges to another member. The org must always have at least one admin.

**FR-1.6** A user can switch between orgs they belong to within the web UI. The active org determines which jobs and API keys are visible.

**FR-1.7** A user can leave an org they do not own. The org is not deleted.

---

### F2 — API Key Management

**FR-2.1** An org admin can create a named API key scoped to the org. The full key value is shown exactly once at creation; subsequent views show only the key prefix (first 8 characters) plus a masked suffix.

**FR-2.2** An org may have up to 10 active API keys simultaneously.

**FR-2.3** An org admin can revoke any API key. Revocation takes effect immediately; in-flight requests authenticated with that key complete normally.

**FR-2.4** The web UI lists all active API keys for the org, showing name, creation date, last-used date, and prefix.

**FR-2.5** API requests are authenticated by passing the key in the `Authorization: Api-Key <key>` header. A revoked or invalid key returns `401`.

**FR-2.6** All API endpoints that return or modify org data enforce that the authenticated key belongs to the org owning the requested resource.

---

### F3 — Manifest Upload and Job Submission

**FR-3.1** A user submits a SBOM generation job by uploading a single manifest or lock file via the web UI or the `POST /api/v1/sbom/generate/` endpoint.

**FR-3.2** Accepted file formats for v1: `requirements.txt`, `pyproject.toml`, `pixi.lock`, `pixi.toml`, `conda environment.yml`. Unsupported formats return `400` with a clear error listing supported formats.

**FR-3.3** The system automatically detects the manifest format from filename and structural markers. If detection is ambiguous, the user may specify the format explicitly via an optional `manifest_format` parameter.

**FR-3.4** Uploaded manifest files are validated before queuing: MIME type checked, file size must not exceed 50 MB, content parsed with safe loaders only (no `eval`, no `exec`). Invalid files are rejected with `400` before a task is enqueued.

**FR-3.5** On successful submission the system returns `202 Accepted` with a `task_id`, `status_url`, and `estimated_seconds` (a rough processing time estimate based on manifest format and file size). The manifest file and connection are released immediately; processing continues asynchronously.

**FR-3.6** The user selects the SBOM output format at submission time. Accepted values: `cdx-json` (default), `cdx-xml`, `spdx-2.3`. SPDX 3.0 is out of scope for v1.

**FR-3.7** The job record is owned by the submitting org. A user submitting under Org A cannot see or interact with the same job when acting under Org B, even if they belong to both.

**FR-3.8** At submission the user provides four **required** provenance fields that are captured with the upload and embedded in the generated SBOM's document metadata: **Application ID** (free-text application identifier), **Application Component Name** (the component the manifest describes), **Repository URL** (the GitHub repository where the manifest normally lives; validated as a URL), and **Source Branch** (the branch the uploaded manifest came from). These are stored on the manifest/job record and written into the SBOM metadata at generation (FR-4.4): for CycloneDX into `metadata.component` (name), a `vcs` external reference (repository URL), and metadata properties (`application:id`, `vcs:branch`); for SPDX into the document/root package name, a VCS external reference, and annotations (best-effort).

---

### F4 — SBOM Generation Pipeline

**FR-4.1** Each submitted job is processed by an asynchronous Celery pipeline. The pipeline executes in eight phases with progress reported at each phase boundary (0–100%).

**FR-4.2** Phase sequence and approximate progress thresholds:

| Phase | Name                             | Progress  |
|-------|----------------------------------|-----------|
| 1     | Detect and parse manifest        | 0–15%     |
| 2     | Resolve transitive dependencies  | 15–40%    |
| 3     | Generate SBOM document           | 40–55%    |
| 4     | Vulnerability scan               | 55–80%    |
| 5     | License compliance analysis      | 80–88%    |
| 6     | Dependency graph generation      | 88–93%    |
| 7     | Version currency analysis        | 93–97%    |
| 8     | Persist artifacts                | 97–100%   |

Phases 4–7 run in parallel; the pipeline waits for all four to complete before Phase 8.

**FR-4.3** The transitive dependency resolution strategy by format:

- `pixi.lock`: parse with PyYAML safe loader (pixi.lock is YAML-formatted despite the `.lock` extension); full transitive tree present in lock file
- `pixi.toml`: parse TOML; invoke `uv pip compile` as subprocess for transitive resolution
- `pyproject.toml`: parse with `tomllib`; invoke `uv pip compile` if no lock file present
- `requirements.txt`: parse with `packaging.requirements.Requirement`; invoke `uv pip compile` for transitive resolution
- `conda environment.yml`: parse with PyYAML safe loader; invoke `conda`/`mamba` solver. conda/mamba is a required runtime dependency for the deployed application; if the solver is unavailable the job fails with a descriptive error.

**FR-4.4** The SBOM is generated from the resolved package list using `cyclonedx-python-lib` (CycloneDX output) or `lib4sbom` (SPDX output). The resolved package list is the shared input to both libraries; format selection determines which serializer is invoked.

**FR-4.5** If Phase 3 (SBOM generation) fails, the job fails entirely. If any of Phases 4–7 (analysis) fail, the job completes with a partial result: the SBOM is available for download and the UI indicates which analysis reports are unavailable, with the failure reason.

**FR-4.6** Job time limits: 25-minute soft limit triggers `SoftTimeLimitExceeded` — the task catches this exception, marks the job `FAILED` with reason `"soft_timeout"`, releases any held resources, and does not return a partial SBOM. The 30-minute hard limit forcibly terminates the worker process; the job is marked `FAILED` with reason `"hard_timeout"` by a cleanup sweep on the next status poll. Both timeout reasons are surfaced to the user in the job history and results page.

**FR-4.7** A client can poll `GET /api/v1/sbom/status/{task_id}/` to retrieve current status (`PENDING`, `PROGRESS`, `SUCCESS`, `FAILURE`), progress percentage (0–100), current phase name, and — on success — a `result_url`.

---

### F5 — Analysis Reports

**FR-5.1 Vulnerability Report** — The service queries the OSV batch API (`POST https://api.osv.dev/v1/querybatch`) with all resolved packages. The report lists each vulnerable package, the CVE/GHSA identifier(s), CVSS score and severity (Critical/High/Medium/Low) where available, CWE classification (enriched from NVD where OSV data is absent), and a link to the OSV advisory. Packages with no known vulnerabilities are not listed.

**FR-5.2 License Compliance Report** — The service extracts the declared license for each resolved package from PyPI metadata. Packages are grouped into four tiers displayed in descending order of attention required:

- **Strong Copyleft — Attention Required**: `AGPL-3.0-only`, `GPL-2.0-only`, `GPL-2.0-or-later`, `GPL-3.0-only`, `GPL-3.0-or-later` — embedding in a differently-licensed project carries legal risk; network use triggers copyleft for AGPL
- **Weak Copyleft — Review Recommended**: `LGPL-2.1-only`, `LGPL-2.1-or-later`, `LGPL-3.0-only`, `LGPL-3.0-or-later` — generally safe for Python import-style linking but surfaces for awareness
- **Unknown**: packages with no declared license or a non-SPDX license identifier — legally equivalent to "all rights reserved" until confirmed otherwise
- **Permissive**: all other SPDX identifiers (MIT, Apache-2.0, BSD-*, ISC, etc.) — no action required

**FR-5.3 Dependency Graph** — The service builds a directed acyclic graph (DAG) of all resolved packages and their `depends-on` relationships using NetworkX. Phase 6 of the pipeline produces two outputs: structured `{nodes, edges}` JSON (for the interactive React view) and a static Graphviz SVG artifact available for download.

**FR-5.4 Version Currency Report** — For each resolved package, the service fetches the latest stable version from the PyPI JSON API and classifies the installed version by release series distance: `current` (same release series as latest, e.g. 5.2.1 vs 5.2.3), `behind-1` (one release series behind, e.g. 5.1.x when 5.2.x is latest), `behind-2+` (two or more release series behind, e.g. 4.x when 5.2.x is latest, including major-version gaps), or `unknown` (version data unavailable). High-priority packages with documented LTS versions (Django, Python) use an LTS-aware classification. The set of LTS-tracked packages and their known LTS versions is configurable via an environment variable (`SBOM_LTS_REGISTRY`) that accepts a JSON mapping of package name to LTS version string, allowing operators to extend or override the built-in defaults.

**FR-5.5 External API Caching** — PyPI JSON API responses are cached in Redis with a 1-hour TTL. OSV API responses are cached in Redis with a 24-hour TTL. Cache keys are scoped by package name + version; since vulnerability and version data is public, this cache is safely shared across orgs for the same package+version pair.

---

### F6 — Results Web UI

**FR-6.1** On job completion, the results page presents output in five tabs: **Overview**, **Vulnerabilities**, **Licenses**, **Dependency Graph**, and **Version Currency**.

**FR-6.2 Overview tab** — Summary statistics: total package count, vulnerable package count, license category breakdown (permissive / copyleft / unknown), packages at current / behind / unknown versions, and a download button for the SBOM artifact (format as submitted). Links to each analysis tab.

**FR-6.3 Vulnerabilities tab** — Sortable table of vulnerable packages: package name, installed version, CVE/GHSA IDs, CVSS score, severity (Critical / High / Medium / Low), advisory link. Filterable by severity. Zero-finding state displayed explicitly ("No vulnerabilities found in X packages").

**FR-6.4 Licenses tab** — Packages grouped into four tiers: Strong Copyleft (Attention Required), Weak Copyleft (Review Recommended), Unknown, Permissive — displayed in that order. Each package links to its PyPI page. Tiers with zero packages are collapsed by default.

**FR-6.5 Dependency Graph tab** — Interactive dependency graph rendered inline using Cytoscape.js with a hierarchical dagre layout. Supports zoom, pan, node drag, and hover-to-highlight. A "Download SVG" button exports the static Graphviz artifact.

**FR-6.6 Version Currency tab** — Table of all packages with installed version, latest version, and currency status badge (Current / Behind / Unknown). Sortable by status. Packages classified `behind-2+` displayed first by default.

**FR-6.7** If any analysis phase failed (per FR-4.5), the corresponding tab displays a failure notice with the error reason rather than results. The SBOM download and successful report tabs remain available.

**FR-6.8** The results page URL is stable and shareable within the org. Any member of the same org with the URL can view the results. Users outside the org receive `403`.

---

### F7 — Job History Dashboard

**FR-7.1** The job history dashboard lists all SBOM generation jobs for the active org, most recent first, with columns: submitted time, manifest filename, manifest format, output format, status (with visual indicator), and a link to results.

**FR-7.2** In-progress jobs display the current progress percentage and phase name, updated via JavaScript polling of `GET /api/v1/sbom/status/{task_id}/` every 5 seconds. No WebSocket infrastructure required. Real-time WebSocket updates are deferred to v2.

**FR-7.3** Jobs in `FAILED` state display a failure reason summary in the list.

**FR-7.4** The dashboard supports filtering by status (All / In Progress / Completed / Failed) and manifest format.

**FR-7.5** The job list is paginated at 25 jobs per page.

---

### F8 — Artifact Retention and Cleanup

**FR-8.1** All generated artifacts (SBOM files, analysis report files) are automatically deleted 10 days after the job completed. The job record and its metadata (status, package count, summary statistics) are retained indefinitely.

**FR-8.2** A scheduled Celery Beat job runs daily to delete expired artifacts. Deletion cascades to the storage backend (S3 / local filesystem) and clears the artifact key from the job record.

**FR-8.3** On the results page and job history, expired jobs display a notice that artifacts are no longer available, with the expiry date. The job record (status, package count, summary statistics) remains visible.

**FR-8.4** A user can manually delete a job's artifacts before the 10-day TTL. The job record is retained.

**FR-8.5** Org admins can bulk-delete all artifacts for the org.

---

## Non-Functional Requirements

### Multi-Tenancy Isolation

**NFR-1.1** Every data model that stores org-owned data includes an `org` foreign key. All ORM queries in the application are filtered by the authenticated org. Direct-object-reference attacks (accessing `task_id` belonging to another org) return `404`, not `403`, to avoid leaking existence information.

**NFR-1.2** The Redis result backend stores task state under keys prefixed with `{org_id}:{task_id}`. Artifact storage paths follow `sbom-results/{org_id}/{task_id}/{filename}`.

### Performance

**NFR-2.1** Expected pipeline completion times (single Celery worker, 4 cores):

- < 50 packages: under 35 seconds
- 50–250 packages: under 135 seconds
- 250–1000 packages: under 7 minutes
- 1000+ packages: under 25 minutes (within 30-minute task limit)

**NFR-2.2** The web UI results page must load (excluding graph rendering) in under 3 seconds once artifacts are available.

### Security

**NFR-3.1** Manifest files are parsed using safe loaders only (`tomllib`, `PyYAML` safe load). No manifest content is passed to `eval`, `exec`, or any shell command without sanitization.

**NFR-3.2** Generated artifact URLs are presigned (S3) or session-authenticated (local). No artifact is publicly accessible without authentication.

**NFR-3.3** API keys are stored as `PBKDF2`-hashed values; only the hash is persisted. The plaintext key is shown once at creation.

**NFR-3.4** File uploads are validated for MIME type and file size before being accepted. Zip bombs and path traversal attempts are rejected.

### Rate Limiting

**NFR-4.1** Per-org concurrent job limit is configurable via the `SBOM_MAX_CONCURRENT_JOBS_PER_ORG` environment variable, defaulting to `5`. Submissions beyond the active limit return `429` with a `Retry-After` header. The default of 5 is sized for a single-host Docker Compose deployment with 4 CPU cores.

**NFR-4.2** External API calls (OSV, PyPI JSON) within a task are rate-limited via `requests-ratelimiter`: 1 req/s for OSV, 5 req/s for PyPI.

### Deployment and Operations

**NFR-5.1** The service is distributed as a Docker Compose application. A `docker compose up` from a cloned repository with a configured `.env` file starts the full stack (Django, Celery worker, Celery Beat, Redis, PostgreSQL, MinIO for local S3).

**NFR-5.2** All configuration is driven by environment variables. No secrets are committed to the repository.

**NFR-5.3** Structured logging via `structlog` in JSON format. All log entries include `org_id`, `task_id` (where applicable), and `user_id`.

**NFR-5.4** The project is licensed under Apache 2.0.

### Observability

**NFR-6.1** Each pipeline phase emits a structured log entry on start and completion, including phase name, duration, and package count processed.

**NFR-6.2** Celery task failures are logged with full traceback and the manifest format that triggered the failure.

---

## API Design

The full REST API surface (all endpoints require `Authorization: Api-Key <key>`):

| Method   | Path                                                    | Description                                              |
|----------|---------------------------------------------------------|----------------------------------------------------------|
| `POST`   | `/api/v1/sbom/generate/`                                | Submit manifest; returns `202` with `task_id`, `status_url`, `estimated_seconds` |
| `GET`    | `/api/v1/sbom/status/{task_id}/`                        | Poll job status, progress, current phase                 |
| `GET`    | `/api/v1/sbom/result/{task_id}/`                        | Download SBOM artifact (or `303` to presigned URL)       |
| `GET`    | `/api/v1/sbom/result/{task_id}/reports/vulnerabilities/`| Vulnerability report (JSON)                              |
| `GET`    | `/api/v1/sbom/result/{task_id}/reports/licenses/`       | License compliance report (JSON)                         |
| `GET`    | `/api/v1/sbom/result/{task_id}/reports/graph/`          | Dependency graph (PyVis HTML or Graphviz SVG via `Accept` header) |
| `GET`    | `/api/v1/sbom/result/{task_id}/reports/versions/`       | Version currency report (JSON)                           |
| `GET`    | `/api/v1/jobs/`                                         | List org's jobs (paginated, filterable)                  |
| `DELETE` | `/api/v1/jobs/{task_id}/artifacts/`                     | Delete artifacts for a job                               |
| `POST`   | `/api/v1/keys/`                                         | Create API key (admin only)                              |
| `GET`    | `/api/v1/keys/`                                         | List API keys for org                                    |
| `DELETE` | `/api/v1/keys/{key_id}/`                                | Revoke API key (admin only)                              |
| `GET`    | `/api/v1/orgs/{org_id}/members/`                        | List org members                                         |
| `POST`   | `/api/v1/orgs/{org_id}/members/`                        | Create member account (admin only)                       |
| `DELETE` | `/api/v1/orgs/{org_id}/members/{user_id}/`              | Remove member (admin only)                               |

---

## Success Metrics

- **Pipeline completion rate** ≥ 95% of submitted jobs complete successfully (not timed out, not errored in Phase 3)
- **Time to first SBOM** median ≤ 35 seconds for manifests under 50 packages
- **Manifest format coverage** all 5 v1 formats accepted and processed in ≥ 99% of valid uploads
- **Analysis availability** all 4 analysis reports generated in ≥ 90% of successful jobs
- **OSS adoption** (post-release) GitHub stars, Docker Hub pulls, and third-party references as lagging indicators

**Counter-metrics** (watch for degradation):

- Job failure rate by manifest format — detects format-specific parser regressions
- p99 pipeline latency — detects external API slowdowns (OSV, PyPI)
- Cross-org access attempts returning non-404 — security regression indicator
- Artifact storage growth rate — detects cleanup job failure

---

## Open Questions

All open questions resolved during Discovery.

| #      | Question                | Resolution                                                                 |
|--------|-------------------------|----------------------------------------------------------------------------|
| OQ-1   | OSS license             | Apache 2.0                                                                 |
| OQ-2   | License flag list       | Four-tier model: Strong Copyleft / Weak Copyleft / Unknown / Permissive    |
| OQ-3   | Per-org job limit       | Configurable via `SBOM_MAX_CONCURRENT_JOBS_PER_ORG`, default 5             |
| OQ-4   | Invitation flow         | Admin creates account directly (email + temp password); no SMTP dependency |
| OQ-5   | UI refresh strategy     | 5-second JavaScript polling; WebSocket deferred to v2                      |
| OQ-6   | conda best-effort scope | conda/mamba required runtime dep; job fails with descriptive error if absent|

---

## Out of Scope — v1

- OAuth / SSO authentication (deferred to v2)
- `uv.lock` and `poetry.lock` manifest formats (deferred to v2; lockfile parsers are low-complexity additions)
- SPDX 3.0 output (lib4sbom SPDX 3.0 support is experimental as of 2026-07-03)
- VEX (Vulnerability Exploitability eXchange) documents
- Real-time WebSocket progress updates (HTTP polling is sufficient for v1)
- Kevin-hosted public SaaS instance
- Multi-project portfolio analysis / cross-project dashboards
- CI/CD webhook integrations (API-first design enables this without a dedicated integration layer)
- AI-assisted vulnerability triage
- Billing, usage quotas, or tiered access
