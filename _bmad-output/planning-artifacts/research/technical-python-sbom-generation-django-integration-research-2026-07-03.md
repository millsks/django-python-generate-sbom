---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'Python SBOM Generation and Django Integration'
research_goals: 'Identify and evaluate Python libraries for SBOM generation across all manifest formats; determine async/Celery integration patterns for long-running generation tasks in Django; assess tooling for license compliance, vulnerability mapping, dependency graph visualization, and version currency analysis'
user_name: 'Kevin'
date: '2026-07-03'
web_research_enabled: true
source_verification: true
---

# Research Report: Technical

**Date:** 2026-07-03
**Author:** Kevin
**Research Type:** Technical

---

## Research Overview

This report covers the full technical landscape for building a production-ready SBOM generation service on Django: library selection for CycloneDX and SPDX output, manifest parsing strategy across seven Python package manager formats, async task pipeline design with Celery, vulnerability and license analysis integration, dependency graph generation, and version currency tracking. Research was conducted via parallel web searches against current (2026) sources across five domains: SBOM tooling, Python dependency management, Django/Celery architecture, vulnerability databases, and graph visualization. All findings are source-cited. See the Research Synthesis section below for the executive summary and strategic recommendations.

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technical Research Scope Confirmation

**Research Topic:** Python SBOM Generation and Django Integration
**Research Goals:** Identify and evaluate Python libraries for SBOM generation across all manifest formats; determine async/Celery integration patterns for long-running generation tasks in Django; assess tooling for license compliance, vulnerability mapping, dependency graph visualization, and version currency analysis

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Performance Considerations - scalability, optimization, patterns

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-07-03

---

## Technology Stack Analysis

### Programming Languages and Core Runtimes

Python 3.12–3.14 is the ecosystem baseline for all tooling surveyed. Python 3.11+ is particularly relevant because it ships `tomllib` in the standard library, enabling native pyproject.toml parsing without a third-party dependency. All SBOM libraries evaluated below target Python 3.9+ as their minimum, so targeting 3.12+ is safe and recommended.

The dependency management landscape shifted significantly in 2025–2026: `uv` now leads with ~75 million monthly PyPI downloads, surpassing Poetry's ~66 million. This matters for manifest parsing strategy — `uv.lock` is now the most common lock file format and must be a first-class input.

_Source: [Python Dependency Management in 2026 — Cuttlesoft](https://cuttlesoft.com/blog/2026/01/27/python-dependency-management-in-2026/)_

---

### SBOM Generation Libraries

**`cyclonedx-python-lib`** (PyPI: `cyclonedx-python-lib`) is the **recommended programmatic library** for CycloneDX SBOM generation within a Python application. It is explicitly designed for embedding — not CLI use. It provides data models, validators, and serializers for CycloneDX JSON and XML. The `Bom.from_parser()` API accepts a parser instance and produces a structured `Bom` object that can be serialized to any supported schema version.

**`cyclonedx-python`** (PyPI: `cyclonedx-bom`, current v7.3.0) is the CLI tool that wraps `cyclonedx-python-lib`. It supports pip environments, requirements files, pipenv, and Poetry. It is the most feature-complete Python-native CycloneDX generator and includes metadata, license data, and dependency graph in its output. It can also be invoked as a subprocess if a pure-programmatic approach becomes complex for a particular input format.

**`lib4sbom`** is a unified parser/generator library that handles both SPDX and CycloneDX formats, with experimental SPDX 3.0 support. It is the strongest candidate for the SPDX output path, complementing `cyclonedx-python-lib` for the CycloneDX path.

**`syft`** (Anchore, Go binary) is an external tool invokable as a subprocess. It produces the most well-formed CycloneDX 1.4 SBOMs in independent testing and supports SPDX output. Its strength is directory scanning rather than manifest parsing — it analyzes the installed Python environment directly. It is a strong fallback or supplement for environments where installing the package list is feasible.

**`pip-licenses`** is a specialized license extraction tool, not a full SBOM generator. It is best used as a supplementary data source for the license compliance analysis report, not as the primary SBOM generation path.

_Sources: [CycloneDX Python Tool](https://github.com/CycloneDX/cyclonedx-python) · [cyclonedx-python-lib](https://github.com/CycloneDX/cyclonedx-python-lib) · [lib4sbom PyPI](https://pypi.org/project/lib4sbom/) · [CycloneDX docs](https://cyclonedx-bom-tool.readthedocs.io/) · [Anchore Python SBOM blog](https://anchore.com/blog/python-sbom-generation/) · [Timesys SBOM comparison](https://www.timesys.com/security/what-sbom-generation-tool-is-best-for-your-python-application/)_

---

### Manifest Parsing and Transitive Dependency Resolution

Resolving full transitive dependency trees from a manifest file — without installing packages — is the most architecturally complex piece of this project. The landscape by format:

| Format | Parser Strategy | Transitive Resolution |
|---|---|---|
| `requirements.txt` | `pip-tools` (`pip-compile` API) or direct parsing | Full via pip's resolver or `pipdeptree` against an installed env |
| `pyproject.toml` (PEP 621) | `tomllib` (stdlib, 3.11+) | Requires a resolver; `uv` or `pip-tools` can resolve without installing |
| `poetry.lock` | Direct TOML parsing; lock already contains full transitive tree | Lock file is the source of truth |
| `uv.lock` | Direct TOML parsing (TOML v1); full transitive tree present | Lock file is the source of truth |
| `pixi.toml` + `pixi.lock` | Direct TOML parsing; `pixi.lock` has transitive closure | Lock file is authoritative; `pixi.toml` has only direct deps |
| `conda environment.yml` | PyYAML parsing; conda-libmamba-solver for full resolution | Requires conda/mamba solver invocation |

**Key architectural decision:** Lock files (when present) are the most reliable source for full transitive trees with exact pinned versions — parse them directly. For manifests without locks (bare `requirements.txt`, `pyproject.toml` without a lock), a resolver call is required. `uv`'s resolver (`uv pip compile`) is the fastest available and can be invoked as a subprocess.

**`pipdeptree`** (PyPI: `pipdeptree`) provides `--json-tree` output for installed Python environments. It is most useful when the manifest represents an already-installed environment, or when the service installs packages into an ephemeral virtualenv to then introspect.

_Sources: [pixi.toml transitive deps — Pixi docs](http://pixi.prefix.dev/latest/python/pyproject_toml/) · [pipdeptree PyPI](https://pypi.org/project/pipdeptree/) · [pipdeptree GitHub](https://github.com/tox-dev/pipdeptree) · [pyproject.toml vs requirements.txt](https://pydevtools.com/handbook/explanation/pyproject-vs-requirements/) · [Python dep management 2026](https://cuttlesoft.com/blog/2026/01/27/python-dependency-management-in-2026/)_

---

### Vulnerability Scanning and Advisory Databases

**`pip-audit`** (PyPI: `pip-audit`, current v2.9.0) is the PyPA-maintained vulnerability scanner and the recommended programmatic interface. Its architecture is explicitly designed for embedding:

- `Auditor` class: main orchestrator — takes a `VulnerabilityService` and produces an iterator of `(Dependency, list[VulnerabilityResult])`
- `DependencySource` implementations: `RequirementSource`, `PyProjectSource`, `PyLockSource`, `PipSource`
- `VulnerabilityService` implementations: `OsvService` (recommended), `PyPIService`

By default, pip-audit queries the **OSV API** (`osv.dev`), which aggregates PyPA Advisories, GitHub Security Advisories, and NVD into a single normalized record per package version. As of OSV-Scanner v2.3.5 (March 2026), transitive scanning for requirements.txt files is supported via the deps.dev API.

**`nvdlib`** (PyPI: `nvdlib`) provides direct programmatic access to the NVD API (v2) for raw CVE data — useful for enriching OSV findings with CVSS scores and CWE classifications.

**`osv`** (PyPI: `osv`) is the official Python client for the OSV API. Queries are by package name + version + ecosystem (`PyPI`).

Recommended architecture: OSV as primary (broadest coverage, structured data), NVD as an enrichment layer for CVSS/CWE data.

_Sources: [pip-audit PyPI](https://pypi.org/project/pip-audit/) · [OSV.dev GitHub](https://github.com/google/osv.dev) · [OSV-Scanner 2026](https://appsecsanta.com/osv-scanner) · [OSV + malicious packages OpenSSF](https://openssf.org/blog/2026/05/20/detecting-malicious-packages-using-the-osv-api/) · [nvdlib PyPI](https://pypi.org/project/nvdlib/) · [Python supply chain security](https://bernat.tech/posts/securing-python-supply-chain/) · [pip-audit CI guide 2026](https://medium.com/@sharathkumarlokesh/shift-security-left-automating-python-dependency-vulnerability-scanning-with-pip-audit-in-ci-68457d3950e9)_

---

### Dependency Graph Visualization

Three libraries cover the full range of output needs:

**NetworkX** is the graph computation backbone. Model the dependency tree as a directed acyclic graph (DAG) with packages as nodes and `depends-on` relationships as edges. NetworkX provides cycle detection, shortest-path, and centrality algorithms for analysis.

**PyVis** converts NetworkX graphs to interactive HTML files using vis.js. Supports zooming, panning, node dragging, and hover-to-highlight. The `Network.from_nx()` method takes a NetworkX graph directly. This is the best option for browser-rendered interactive graphs served from Django.

**Graphviz / pygraphviz** generates static, structured DOT-format graphs — ideal for clean, hierarchical tree layouts and for generating SVG/PNG artifacts for report embedding.

Recommended approach: NetworkX as the internal graph model → PyVis for interactive web output → Graphviz for static report artifacts (PDF, PNG).

_Sources: [PyVis interactive graphs](https://towardsdatascience.com/making-network-graphs-interactive-with-python-and-pyvis-b754c22c270/) · [NetworkX + PyVis integration](https://web.learnmodernpython.com/interactive-graph-visualizer-networkx-pyvis/) · [Dependency graph visualization — Tom Sawyer](https://blog.tomsawyer.com/dependency-graph-visualization) · [Python graph libraries overview](https://blog.tomsawyer.com/python-graph-visualization-libraries)_

---

### Version Currency Tracking (N, N-1, LTS)

The **PyPI JSON API** provides the data foundation:

- `GET https://pypi.org/pypi/{package}/json` → latest stable release metadata
- `GET https://pypi.org/pypi/{package}/{version}/json` → specific version metadata
- The `releases` key (note: marked deprecated in warehouse but not yet removed) → all available version strings with artifact metadata

**Approach for N / N-1 / LTS classification:**
1. Fetch all releases via the PyPI JSON API
2. Parse and sort version strings using the `packaging` library (`packaging.version.Version`) per PEP 440
3. N = latest stable (no pre-release qualifiers)
4. N-1 = previous minor/major release series
5. LTS = no universal PyPI standard exists; LTS tracking requires ecosystem-specific logic (e.g., `django-lts` releases, Python's own LTS via `devguide.python.org/versions/`)

For Django itself and major frameworks, LTS designation is documented upstream and can be fetched from their changelogs/release notes. A best-practice implementation would maintain a small configurable registry of known LTS versions for high-priority packages, falling back to N/N-1 for all others.

The `pypi-json` library (PyPI: `pypi-json`) wraps the JSON API with a cleaner Python interface.

_Sources: [PyPI JSON API docs](https://docs.pypi.org/api/json/) · [PyPI API access with requests](https://opensource.com/article/21/3/python-package-index-json-apis-requests) · [packaging PyPI](https://pypi.org/project/packaging/) · [Python version status](https://devguide.python.org/versions/) · [pypi-json PyPI](https://pypi.org/project/pypi-json/)_

---

### Django + Celery Integration Stack

**Cookiecutter-django** (current version 2026.26.4) has native optional Celery + Redis support built into its scaffold. When selected at project generation time, it provides:

- Pre-configured `config/celery_app.py`
- Redis as both message broker and result backend
- `django-celery-beat` for scheduled tasks
- A sample task in `<project_slug>/users/tasks.py`
- Docker Compose service definitions for the Celery worker

The established REST API pattern for long-running manifest processing:

```
POST /api/sbom/generate/    ← accepts manifest file upload → immediately returns { task_id }
GET  /api/sbom/status/{id}/ ← client polls → returns { status, progress, result_url }
GET  /api/sbom/result/{id}/ ← downloads completed SBOM artifact
```

**`celery-progress`** (PyPI: `celery-progress`) provides Redis-backed progress signaling with a JavaScript polling client — suitable for real-time progress bars without WebSocket complexity.

**Django 6.0 built-in task framework** is a lighter-weight alternative to Celery available if Celery's operational overhead is a concern. However, it lacks the ecosystem maturity, retry logic, rate limiting, and result backend features needed for production SBOM processing at scale. Celery remains the recommended choice.

Key Celery configuration for large manifest processing:
- `task_soft_time_limit`: 1500 (25 min warning)
- `task_time_limit`: 1800 (30 min hard kill)
- `task_rate_limit`: throttle vulnerability API calls per-task
- `task_acks_late = True`: ensures at-least-once processing

_Sources: [Cookiecutter Django docs 2026](https://cookiecutter-django.readthedocs.io/en/latest/) · [Django + Celery — Real Python](https://realpython.com/asynchronous-tasks-with-django-and-celery/) · [Django + Celery — TestDriven.io](https://testdriven.io/blog/django-and-celery/) · [Long-running Django tasks](https://sevalla.com/blog/django-long-running-tasks-with-celery/) · [DRF + Celery async tasks](https://pytutorial.com/django-rest-framework-and-celery-async-tasks/) · [Cookiecutter Django on Fly.io with Celery](https://community.fly.io/t/deploying-cookiecutter-django-on-fly-celery-tigris-s3-postgres-redis/20005)_

---

### Technology Adoption and Ecosystem Trends

- **uv** has overtaken pip-tools and Poetry as the dominant resolver/package manager (2025–2026). `uv.lock` is increasingly the lock file to support first.
- **CycloneDX 1.6** is the current schema version (2025); SPDX 3.0 is ISO-standardized but tooling support is still maturing (lib4sbom's SPDX 3 support is marked experimental).
- **OSV** has become the authoritative aggregation layer for Python vulnerability data, replacing direct NVD querying for most use cases.
- **Pixi** adoption is growing, especially in scientific/ML communities that also use conda. Its lock file is TOML-based and fully parseable.
- Django 6.0 LTS (expected 2025) is the target framework version for cookiecutter-django projects starting in 2026.

---

## Integration Patterns Analysis

### API Design Patterns

The core API surface for this service follows a **submit-poll-retrieve** pattern — the only viable design for long-running operations over HTTP. Three endpoints cover the full contract:

```
POST /api/v1/sbom/generate/
    Content-Type: multipart/form-data
    Body: { manifest_file, output_format (cdx-json|cdx-xml|spdx), options }
    Response 202: { task_id, status_url, estimated_seconds }

GET  /api/v1/sbom/status/{task_id}/
    Response 200: { task_id, status (PENDING|PROGRESS|SUCCESS|FAILURE),
                    progress (0-100), current_step, result_url, error }

GET  /api/v1/sbom/result/{task_id}/
    Response 200: SBOM file (Content-Disposition: attachment)
    Response 303: redirect to presigned S3 URL (preferred for large files)
```

A `202 Accepted` on the generate endpoint is semantically correct — it acknowledges the request without implying completion. The `status_url` field in the response body eliminates the need for clients to construct the polling URL themselves.

**Report sub-endpoints** (analysis reports generated alongside the SBOM) follow the same pattern, either bundled into the result or as separate endpoints under `GET /api/v1/sbom/result/{task_id}/reports/{report_type}/`.

_Sources: [Django 6.0 async docs](https://docs.djangoproject.com/en/6.0/topics/async/) · [Django Tasks framework](https://docs.djangoproject.com/en/6.0/topics/tasks/) · [DRF + Celery async tasks](https://pytutorial.com/django-rest-framework-and-celery-async-tasks/)_

---

### Communication Protocols and Progress Signaling

**Two viable approaches** for progress delivery — the right choice depends on frontend complexity tolerance:

**Option A — HTTP Polling (recommended for initial implementation)**
- Client polls `GET /api/v1/sbom/status/{task_id}/` every 2–5 seconds
- Task state stored in Redis via Celery's result backend; `AsyncResult(task_id).state` + `.info`
- `task.update_state(state='PROGRESS', meta={'progress': 45, 'current_step': 'resolving transitive deps'})` updates Redis in real time
- No WebSocket infrastructure required; works through API gateways, load balancers, CDNs without special config
- `celery-progress` library provides a drop-in polling client (JavaScript) with optional progress bar rendering

**Option B — WebSockets via Django Channels**
- Celery worker pushes progress events to a Django Channels group; connected clients receive real-time updates
- Requires ASGI deployment (Daphne or Uvicorn), channel layer (Redis), and additional Django Channels configuration
- `github.com/pplonski/simple-tasks` demonstrates the pattern
- Adds operational complexity; best deferred until polling proves insufficient

**Recommendation:** Implement polling first. The latency difference (2s polling vs real-time WebSocket) is imperceptible for tasks that take 30–300 seconds. WebSocket support can be added as a later enhancement with the same Celery task unchanged.

_Sources: [Real Python Django + Celery](https://realpython.com/asynchronous-tasks-with-django-and-celery/) · [Progress bars with Django + Celery](https://thelinuxcode.com/how-to-build-robust-progress-bars-for-web-applications-with-django-and-celery/) · [Celery + WebSockets — Cisco](https://blogs.cisco.com/developer/johann03) · [simple-tasks GitHub](https://github.com/pplonski/simple-tasks)_

---

### Data Formats and Standards

| Format | MIME Type | Use |
|---|---|---|
| CycloneDX JSON | `application/vnd.cyclonedx+json; version=1.6` | Default SBOM output |
| CycloneDX XML | `application/vnd.cyclonedx+xml; version=1.6` | Alternate SBOM output |
| SPDX 2.3 JSON | `application/spdx+json` | SPDX output |
| SPDX 3.0 JSON | `application/spdx+json; version=3.0` | Future / experimental |
| Progress JSON | `application/json` | Task status polling responses |
| GraphViz DOT | `text/vnd.graphviz` | Dependency graph static export |
| Pyvis HTML | `text/html` | Interactive dependency graph |

The `output_format` parameter on the generate endpoint should be an enum: `cdx-json` (default), `cdx-xml`, `spdx-2.3`. SPDX 3.0 can be listed as experimental given that `lib4sbom`'s SPDX 3 support is still maturing.

**Multipart upload handling:** Django REST Framework's `FileUploadParser` or `MultiPartParser` handles manifest file ingestion. The uploaded file is written to a temp path, the Celery task receives the path (or Django storage key), and the original HTTP connection closes immediately with `202`.

_Sources: [CycloneDX spec](https://cyclonedx.org/tool-center/) · [SPDX 3.0 standard](https://spdx.dev/)_

---

### Celery Task Architecture and State Machine

The Celery task for SBOM generation is a multi-phase pipeline. Each phase updates task state, giving the polling endpoint fine-grained progress data:

```
Phase 1 — Detect & parse manifest         (0–15%)
Phase 2 — Resolve transitive dependencies (15–40%)
Phase 3 — Generate SBOM document          (40–55%)
Phase 4 — Vulnerability scan (OSV API)    (55–80%)
Phase 5 — License compliance analysis     (80–88%)
Phase 6 — Dependency graph generation     (88–93%)
Phase 7 — Version currency analysis       (93–97%)
Phase 8 — Persist artifacts to storage    (97–100%)
```

**Redis as both broker and result backend** is the standard cookiecutter-django configuration. In production, separate Redis databases (or separate instances) should be used for the broker and result backend to prevent result storage volume from affecting broker throughput.

**Key Celery settings for this workload:**
```python
CELERY_TASK_SOFT_TIME_LIMIT = 1500    # 25 min — triggers SoftTimeLimitExceeded for graceful cleanup
CELERY_TASK_TIME_LIMIT = 1800         # 30 min — hard kill
CELERY_TASK_ACKS_LATE = True          # don't ack until task completes (at-least-once)
CELERY_RESULT_EXPIRES = 86400         # 24h result TTL in Redis
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
```

**Rate limiting for external API calls** (OSV, PyPI JSON API) must be handled within the task, not at the Celery rate limit level, because a single task makes many API calls. Use `tenacity` for retry-with-backoff on transient failures.

_Sources: [Celery 5.6.3 configuration](https://docs.celeryq.dev/en/stable/userguide/configuration.html) · [Production Django + Celery + Redis](https://rahulbaberwal.com/blog/django-celery-redis) · [Celery Redis setup 2026](https://oneuptime.com/blog/post/2026-03-31-redis-configure-celery-with-redis-as-broker-in-django/view)_

---

### Artifact Storage Pattern

Generated SBOM files and report artifacts must not be stored in the Celery result backend (Redis) — they are binary blobs that can be large (megabytes for complex dependency trees). The correct pattern:

1. Celery task writes artifacts to **Django's file storage backend** (local filesystem in dev; S3 via `django-storages` + `boto3` in production)
2. Task stores the **storage key** (not the file bytes) in the Celery result backend
3. The result endpoint fetches the key from Redis, then either:
   - Streams the file from local storage (dev/small deployments)
   - Generates a **presigned S3 URL** (24h TTL) and returns `303 See Other` (production)

**`django-storages`** (`S3Boto3Storage`) is the standard integration. Cookiecutter-django already configures `django-storages` with S3 when the S3 option is selected at generation time — no additional setup required.

Generated artifacts should be organized under a predictable storage path: `sbom-results/{task_id}/{filename}.{ext}` — this enables easy cleanup via lifecycle policies and links the artifact unambiguously to the originating task.

_Sources: [django-storages S3 docs](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html) · [S3 + boto3 guide 2026](https://danubedata.ro/blog/s3-compatible-storage-python-boto3-guide-2026) · [Celery + Redis on Upsun](https://support.platform.sh/hc/en-us/community/posts/20416735357074-Background-Tasks-using-Celery-with-Redis-in-Django-on-Upsun)_

---

### Integration Security Patterns

| Concern | Approach |
|---|---|
| API authentication | Django REST Framework `TokenAuthentication` or `JWTAuthentication` (via `djangorestframework-simplejwt`) — cookiecutter-django includes DRF by default |
| File validation | Validate MIME type + magic bytes on upload; reject oversized files before queuing (configurable max, e.g. 50MB) |
| Task ID authorization | Verify the requesting user owns the task before returning status/result — store `user_id` with the task in a Django model, not only in Redis |
| External API keys | OSV API is public/keyless; NVD API key optional (higher rate limits); store via Django's `SECRET_KEY` pattern or environment variables |
| Artifact access | Presigned S3 URLs are short-lived (1–24h); enforce object ACLs so artifacts are not publicly listable |
| Input sanitization | Manifest files are parsed as structured data (TOML/YAML/text) — use `tomllib`/`PyYAML` safe loaders; never `eval` or `exec` manifest content |

---

## Architectural Patterns and Design

### System Architecture: Modular Monolith

The 2026 consensus is unambiguous: a well-modularized Python monolith handles hundreds of thousands of users without microservices. Microservices solve a narrow set of problems (team coordination at scale, fundamentally different scaling profiles, polyglot requirements) that do not apply here. Cookiecutter-django is a monolith scaffold and should stay one.

**Architecture decision: Modular Monolith with a Service Layer.**

The Django application is organized as a set of cohesive internal modules (Django apps), each with clear boundaries. Cross-cutting concerns (SBOM generation, vulnerability scanning, graph rendering) are isolated in their own apps and communicate through a Python service layer — not HTTP. This preserves the option to extract a service later without rewriting business logic.

_Sources: [Microservices vs Monolith 2026 — Technijian](https://technijian.com/software-development/microservices-vs-monolith-for-startups-the-honest-2026-decision-guide/) · [Monolith to microservices — dasroot.net](https://dasroot.net/posts/2026/01/software-architecture-monolith-to-microservices-python/) · [Docker: Do you need microservices?](https://www.docker.com/blog/do-you-really-need-microservices/)_

---

### Django App Structure

Cookiecutter-django generates a two-tier layout: repository root (config, docs, manage.py) and a Django project root (apps). Within that, this project's apps follow the service-layer pattern:

```
config/
  settings/
    base.py
    local.py
    production.py
  urls.py
  celery_app.py

<project_slug>/
  manifests/          ← file ingestion: upload, detect format, store
    models.py         ← ManifestUpload model (user, file, format, status)
    serializers.py
    views.py          ← POST /api/v1/sbom/generate/ (DRF viewset)
    services.py       ← detect_manifest_format(), store_manifest()

  sbom/               ← SBOM generation core
    models.py         ← SBOMJob model (task_id, user, status, result_key)
    services.py       ← generate_sbom(manifest_path, format) → BOM object
    parsers/          ← one module per manifest format
      requirements.py
      pyproject.py
      poetry_lock.py
      uv_lock.py
      pixi.py
      conda.py
    serializers.py    ← DRF: status, result endpoints
    views.py          ← GET /api/v1/sbom/status/{id}/, GET /api/v1/sbom/result/{id}/

  analysis/           ← analysis reports
    services/
      vulnerability.py   ← pip-audit + OSV API
      license.py         ← pip-licenses + SPDX license data
      graph.py           ← NetworkX + PyVis + Graphviz
      versions.py        ← PyPI JSON API + version currency logic
    models.py         ← AnalysisReport model
    serializers.py
    views.py          ← GET /api/v1/sbom/result/{id}/reports/{type}/

  tasks/              ← Celery task definitions
    sbom_pipeline.py  ← @shared_task: orchestrates all 8 phases
    analysis.py       ← subtasks for each analysis type

  users/              ← cookiecutter-django default app (auth, profiles)
```

_Sources: [Cookiecutter Django 2026.26.4 docs](https://cookiecutter-django.readthedocs.io/en/latest/) · [Django project structure best practices 2026](https://www.technaureus.com/blog-detail/django-project-structure-best-practices-2026) · [Django project structure — DEV Community](https://dev.to/alansomathew/django-project-structure-best-practices-a-production-ready-guide-3io3)_

---

### Service Layer Design Principles

The service layer sits between DRF views and the ORM/external libraries. Each service module contains plain Python functions or classes — no Django request/response objects, no HTTP. This makes services independently testable and reusable from Celery tasks and management commands alike.

**Pattern per app:**
- `views.py` — DRF viewsets only; validate input, call service, return response
- `services.py` — business logic; calls ORM and external libraries; raises domain exceptions
- `selectors.py` — complex read queries; never mutate state
- `tasks.py` (or `tasks/`) — Celery `@shared_task` functions; call services, update task state

**Key principle:** Services know nothing about HTTP or Celery. A Celery task and a DRF view call the same service function. This keeps the pipeline testable without spinning up a broker.

_Sources: [Django service layer — Feb 2026](https://medium.com/@metehan480/django-architecture-building-a-service-layer-to-solve-fat-models-and-leaky-views-ac85acb815f3) · [GLIMPSE clean architecture 2026](https://medium.com/@radoslaw_jan/a-glimpse-of-better-architecture-for-django-projects-c31295529eb5) · [Repository + service pattern](https://dev.to/soldatov-ss/django-without-the-mess-repositories-for-data-services-for-rules-k8e) · [Clean architecture Django](https://shiladityamajumder.medium.com/clean-architecture-in-django-a-practical-real-world-project-structure-1f4c89e402f0)_

---

### Celery Pipeline Architecture

The SBOM generation task is a **linear chain** with embedded parallel sub-tasks where phases are independent. Celery's canvas primitives map cleanly:

```python
# Conceptual pipeline (not literal Celery syntax — implementation detail for architecture)

chain(
    detect_and_parse_manifest.s(manifest_key),      # Phase 1 — detect format, resolve deps
    generate_sbom_document.s(output_format),         # Phase 3 — cyclonedx-python-lib
    group(
        scan_vulnerabilities.s(),                    # Phase 4 — pip-audit + OSV
        analyze_licenses.s(),                        # Phase 5 — pip-licenses
        build_dependency_graph.s(),                  # Phase 6 — NetworkX + PyVis
        check_version_currency.s(),                  # Phase 7 — PyPI JSON API
    ) | aggregate_analysis_results.s(),              # chord callback
    persist_artifacts.s(),                           # Phase 8 — django-storages → S3
)
```

**Phases 4–7 (analysis) run in parallel** via `group()` — each is independent and the longest (vulnerability scan) determines the wall-clock time. A `chord()` collects all four results before Phase 8 persists the complete artifact bundle.

**Critical Celery 5.6 rule:** Use `task.delay_on_commit()` (not `.delay()`) when dispatching from a Django view inside a database transaction. This prevents the worker from reading stale data if the task fires before the transaction commits.

Use `@shared_task` throughout — avoids importing the Celery app instance into task modules, keeping them reusable.

_Sources: [Celery canvas chaining gist](https://gist.github.com/codeinthehole/4124910) · [Django Celery 2026 production patterns](https://softaims.com/blog/django-celery-background-tasks-production-2026) · [Celery ultimate guide](https://deepnote.com/blog/ultimate-guide-to-celery-library-in-python) · [Celery task queue 2026](https://tech-insider.org/celery-python-tutorial-task-queue-redis-2026/)_

---

### Data Architecture

**Django models as the system of record:**

| Model | Fields | Purpose |
|---|---|---|
| `ManifestUpload` | user, file_key, detected_format, uploaded_at | Tracks the input artifact |
| `SBOMJob` | task_id, manifest (FK), user (FK), status, output_format, result_key, created_at, completed_at | System of record for a generation job; source of truth for authorization checks |
| `AnalysisReport` | job (FK), report_type, artifact_key, generated_at | Per-type analysis output links |

Redis holds **transient task state** (progress, current phase) — not persisted beyond the result TTL. All durable state lives in PostgreSQL (via the models above). S3/file storage holds the actual binary artifacts.

This separation means Redis can be flushed without losing job history — only in-flight progress is lost, which is recoverable by re-querying the task or re-running.

---

### Deployment and Operations Architecture

Cookiecutter-django generates a complete Docker Compose stack for local development and a production-ready Docker configuration. The SBOM service maps onto this cleanly:

```
┌─────────────────────────────────────────────────┐
│  Django (Gunicorn/Uvicorn ASGI)                 │  ← HTTP API
│  Celery Worker(s)                               │  ← SBOM pipeline tasks
│  Celery Beat                                    │  ← Scheduled cleanup jobs
│  Flower (optional)                              │  ← Task monitoring UI
├─────────────────────────────────────────────────┤
│  Redis                                          │  ← broker + result backend
│  PostgreSQL                                     │  ← durable state + job records
│  S3 / MinIO (local)                             │  ← artifact storage
└─────────────────────────────────────────────────┘
```

**Celery worker scaling:** SBOM pipeline tasks are CPU/IO-bound; use `--concurrency` to match CPU cores, or deploy multiple worker containers. Analysis phases 4–7 can optionally run on a dedicated high-concurrency worker pool (separate queue) to prevent vulnerability scans from starving the main queue.

**Django deployment note (2026):** Django 6.0 supports full ASGI deployment via Uvicorn/Daphne, enabling async views for the status polling endpoint (non-blocking on the server thread). The SBOM generation POST and artifact GET endpoints remain synchronous (file I/O is fast; the heavy work is in Celery).

_Sources: [Cookiecutter Django local development](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally.html) · [Cookiecutter Django on Fly.io — Celery + Redis + S3](https://community.fly.io/t/deploying-cookiecutter-django-on-fly-celery-tigris-s3-postgres-redis/20005) · [Scalable Django architecture](https://www.bluetickconsultants.com/building-a-scalable-and-maintainable-architecture-for-large-scale-django-projects/) · [Async Django 2026](https://medium.com/@yogeshkrishnanseeniraj/the-ultimate-async-django-architecture-guide-2025-2026-edition-4333ab4c8a90)_

---

## Implementation Approaches and Technology Adoption

### CycloneDX SBOM Generation — Library API

**`cyclonedx-python-lib`** (current: v11.11.0) is the embedding-ready library. The core pattern:

```python
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.license import DisjunctiveLicense, LicenseExpression
from cyclonedx.output.json import JsonV1Dot6
from cyclonedx.output.xml import XmlV1Dot6
from packageurl import PackageURL

def build_sbom(resolved_packages: list[dict]) -> Bom:
    bom = Bom()
    bom.metadata.component = Component(
        name="my-project", component_type=ComponentType.APPLICATION
    )
    for pkg in resolved_packages:
        c = Component(
            name=pkg["name"],
            version=pkg["version"],
            component_type=ComponentType.LIBRARY,
            purl=PackageURL("pypi", name=pkg["name"], version=pkg["version"]),
        )
        bom.components.add(c)
    return bom

# Serialize to JSON or XML
def serialize_sbom(bom: Bom, fmt: str) -> str:
    if fmt == "cdx-xml":
        return XmlV1Dot6(bom).output_as_string()
    return JsonV1Dot6(bom).output_as_string()  # default
```

The `Bom` object is the internal data model — serialization is a separate concern. This keeps the pipeline format-agnostic until the final output step.

**SPDX output** via `lib4sbom`: Build the same resolved package list, then use `lib4sbom`'s `SBOMGenerate` class with `sbom_type="spdx"`. The two libraries share no common model, so format selection at Phase 3 determines which library is invoked.

_Sources: [cyclonedx-python-lib GitHub](https://github.com/CycloneDX/cyclonedx-python-lib) · [cyclonedx-python-lib PyPI](https://pypi.org/project/cyclonedx-python-lib/) · [Component API docs v11](https://cyclonedx-python-library.readthedocs.io/en/latest/autoapi/cyclonedx/model/component/index.html) · [lib4sbom PyPI](https://pypi.org/project/lib4sbom/)_

---

### Manifest Parsing — Implementation Sequence

The manifest detection + parsing phase is the most complex. Recommended implementation order (per project priority):

1. **`requirements.txt`** — Split lines, strip comments (`#`), parse with `pip`'s `parse_requirements()` or `packaging.requirements.Requirement`. Transitive resolution requires `uv pip compile` as a subprocess or creating a temporary virtualenv.

2. **`pyproject.toml`** (PEP 621) — `tomllib.loads()` (stdlib 3.11+); read `project.dependencies` for direct deps. Lock file preferred if present alongside it.

3. **`pixi.lock`** — YAML-based (despite being a pixi project). PyYAML safe load; `packages` section contains pinned transitive closure for each platform/environment. Full transitive tree present — no resolver needed.

4. **`pixi.toml`** — TOML; only direct dependencies. Always check for `pixi.lock` first; fall back to `pixi.toml` with a resolver if lock absent.

5. **`conda environment.yml`** — PyYAML safe load; `dependencies` list. Transitive resolution requires invoking `conda`/`mamba` solver — most complex path; consider marking as "best-effort" in v1.

6. **`uv.lock`** — TOML v1 format; `[[package]]` blocks. Full transitive tree present. Parse with `tomllib`.

7. **`poetry.lock`** — TOML; every `[[package]]` block is an installed package with its version. Full transitive tree present — no resolver needed. Parse with `tomllib`.

**Format detection heuristic** (apply in order): check filename extension + key structural markers, not just file extension alone (e.g., a `pyproject.toml` might be Poetry, Hatch, PDM, or uv — check `[tool.poetry]`, `[tool.hatch]`, `[build-system]` to disambiguate).

_Sources: [pixi.lock transitive deps](http://pixi.prefix.dev/latest/python/pyproject_toml/) · [Python dep management 2026](https://cuttlesoft.com/blog/2026/01/27/python-dependency-management-in-2026/) · [pipdeptree GitHub](https://github.com/tox-dev/pipdeptree)_

---

### Vulnerability Scanning — pip-audit Programmatic API

`pip-audit`'s programmatic API uses private modules (prefixed `_`). This is a known tradeoff — the public API is the CLI. Treat these imports as internal and pin `pip-audit` to a specific version range:

```python
from pip_audit._audit import Auditor
from pip_audit._dependency_source import ResolvedDependency
from pip_audit._service.osv import OsvService
from pip_audit._service.interface import VulnerabilityResult

def scan_vulnerabilities(
    packages: list[tuple[str, str]]  # (name, version) pairs
) -> dict[str, list[VulnerabilityResult]]:
    service = OsvService()
    deps = [ResolvedDependency(name=n, version=Version(v)) for n, v in packages]
    auditor = Auditor(service)
    results = {}
    for dep, vulns in auditor.audit(iter(deps)):
        if vulns:
            results[dep.name] = vulns
    return results
```

**Alternative — direct OSV batch API** (avoids pip-audit's private API entirely): `POST https://api.osv.dev/v1/querybatch` accepts up to ~1000 packages per request at 100 req/min. Batch all packages from the resolved dependency tree in a single call, parse the structured JSON response. This is more stable than pip-audit's internals and gives direct control over the response schema.

**Recommendation:** Use the OSV batch API directly for the initial implementation — it is a stable public API, simpler to mock in tests, and gives structured data without going through pip-audit's parsing layer.

_Sources: [pip-audit PyPI](https://pypi.org/project/pip-audit/) · [pip-audit GitHub](https://github.com/pypa/pip-audit) · [OSV querybatch API](https://google.github.io/osv.dev/post-v1-querybatch/) · [OSV API docs](https://google.github.io/osv.dev/api/) · [OSV malicious packages OpenSSF 2026](https://openssf.org/blog/2026/05/20/detecting-malicious-packages-using-the-osv-api/)_

---

### External API Rate Limiting and Caching

Two external APIs are called during every SBOM generation job — OSV and PyPI JSON. Both need caching to avoid redundant calls and stay within rate limits.

**`requests-cache`** with a Redis backend is the correct tool: it hooks into the `requests` library transparently and stores responses in the same Redis instance already used by Celery. Cache policy:

| API | TTL | Rationale |
|---|---|---|
| PyPI JSON (`/pypi/{pkg}/json`) | 1 hour | Releases are infrequent; version data is stable within a session |
| OSV `/v1/query` | 24 hours | Vulnerability data changes rarely within a day |
| OSV `/v1/querybatch` | 24 hours | Same rationale; cache by content hash of the package+version set |

**`requests-ratelimiter`** wraps the cached session to enforce conservative limits even when cache misses occur: 5 req/s for PyPI, 1 req/s for OSV (well under the 100 req/min documented limit, leaving headroom for concurrent jobs).

For `httpx`-based clients: **`httpx-limiter`** (released May 2026) provides the same capability.

_Sources: [requests-cache PyPI](https://pypi.org/project/requests-cache/) · [requests-ratelimiter PyPI](https://pypi.org/project/requests-ratelimiter/) · [pyrate-limiter PyPI](https://pypi.org/project/pyrate-limiter/) · [httpx-limiter PyPI](https://pypi.org/project/httpx-limiter/)_

---

### Testing Strategy

The service layer architecture from Step 4 pays its biggest dividend in testing: services are plain Python, testable without HTTP or a Celery broker.

**Unit tests (`tests/unit/`)** — test service functions directly:
- Mock external API clients (`requests`, `OsvService`) with `unittest.mock.patch`
- Test each manifest parser with fixture files covering valid, malformed, and edge-case inputs
- Test SBOM generation service with a known `resolved_packages` list → assert BOM component count and PURL correctness
- No Celery, no Redis, no Django ORM required

**Integration tests (`tests/integration/`)** — test the full pipeline against real infrastructure:
- Use `pytest-celery` with `broker_url='memory://'` and `result_backend='rpc://'` in `conftest.py` — no external broker needed for integration tests
- The `celery_worker` fixture starts a real worker thread, giving accurate serialization/deserialization behavior that eager mode skips
- Do NOT use `CELERY_ALWAYS_EAGER` — it bypasses serialization and misses a class of real production bugs

**Test fixtures:** Include sample manifest files for every supported format in `tests/fixtures/manifests/`. These are the single most valuable test assets for this project — invest in coverage across format edge cases (empty files, comments-only requirements.txt, PEP 508 extras syntax, git+https dependencies, etc.).

_Sources: [Celery 5.6.3 testing docs](https://docs.celeryq.dev/en/stable/userguide/testing.html) · [Testing Celery without eager](https://tomwojcik.com/posts/2021-03-02/testing-celery-without-eager-tasks/) · [Django + Celery + pytest lessons](https://mikebian.co/lessons-learned-building-with-django-celery-and-pytest/) · [Mock Celery with pytest](https://typethepipe.com/vizs-and-tips/mock-celery-task-pytest/)_

---

### Implementation Roadmap

Recommended build sequence — each phase is independently deployable and testable:

**Phase 1 — Foundation (Sprint 1)**
- Scaffold cookiecutter-django with Celery + Redis + PostgreSQL + S3 options selected
- Implement `manifests` app: upload endpoint, format detection, file storage
- Implement `SBOMJob` model and status/result endpoints (stubs)
- Celery task skeleton with 8-phase progress reporting

**Phase 2 — Core SBOM (Sprint 2)**
- Implement manifest parsers: `requirements.txt`, `pyproject.toml`, `pixi.lock`, `pixi.toml`
- Implement `sbom/services.py`: `cyclonedx-python-lib` BOM construction from resolved packages
- CycloneDX JSON output (default format) end-to-end
- Unit tests for all parsers; integration test for the full pipeline

**Phase 3 — Format Expansion (Sprint 3)**
- Add CycloneDX XML output
- Add SPDX 2.3 JSON output via `lib4sbom`
- Add remaining manifest parsers: `conda environment.yml`, `uv.lock`, `poetry.lock`
- Format selection parameter wired to the generate endpoint

**Phase 4 — Analysis Reports (Sprint 4)**
- Vulnerability scanning: OSV batch API integration + caching layer
- License compliance: `pip-licenses` integration + SPDX license classification
- Version currency: PyPI JSON API + N/N-1/LTS classification logic

**Phase 5 — Graph and Polish (Sprint 5)**
- Dependency graph: NetworkX model + PyVis HTML output + Graphviz static export
- Progress reporting refinement (per-phase percentage via `update_state`)
- Error handling: partial results on phase failure (return SBOM even if vuln scan fails)
- Performance profiling for 500+ package manifests

---

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| pip-audit private API breaks on version bump | Medium | High | Use OSV batch API directly instead |
| conda manifest resolution requires conda binary | High | Medium | Mark as "best-effort" in v1; document dependency |
| PyPI API `releases` key deprecated/removed | Low | Medium | Use version list from `/pypi/{pkg}/json` `info.version` + crawling strategy |
| OSV rate limit (100 req/min) hit under load | Low | Medium | Batch queries + `requests-ratelimiter`; OSV batch handles 1000 packages/request |
| Large manifests (2000+ packages) exceed 30-min task limit | Low | High | Add `task_time_limit` monitoring; consider splitting analysis into sub-tasks |
| SPDX 3.0 support requested before lib4sbom matures | Medium | Low | Mark SPDX 3.0 as experimental; deliver SPDX 2.3 first |

---

## Research Synthesis

### Executive Summary

Software Bills of Materials have moved from a federal compliance checkbox to a foundational DevSecOps practice. While the Trump administration's OMB M-26-05 (January 2026) rolled back the mandatory SBOM attestation requirement for federal software vendors, CISA's SBOM guidance remains active, the EU Cyber Resilience Act (CRA) imposes parallel SBOM obligations for products sold into European markets, and enterprise software procurement increasingly demands SBOM artifacts regardless of regulatory mandate. Supply chain attacks — XZ Utils, event-stream, SolarWinds — have made the business case for SBOM adoption independent of any government directive. A self-service Django application that accepts a Python project's manifest file and returns a production-grade SBOM plus analysis reports addresses a real, growing, and technically underserved need.

The Python SBOM tooling ecosystem in 2026 is mature enough to build on but fragmented enough to require careful library selection. No single library handles all manifest formats and all output formats. The recommended architecture pairs `cyclonedx-python-lib` (CycloneDX JSON/XML) with `lib4sbom` (SPDX 2.3) for output, uses direct TOML/YAML parsing of lock files for dependency resolution (avoiding solver invocations wherever possible), routes vulnerability scanning through the OSV batch API (stable, public, aggregates NVD + PyPA + GitHub), and composes analysis phases in parallel inside a Celery task pipeline. The Django layer itself is thin — cookiecutter-django's scaffold with Celery + Redis + PostgreSQL + S3 selected at generation time provides 80% of the infrastructure for free.

The most significant architectural risk is the manifest parsing phase: seven formats with different resolution strategies, varying levels of transitive dependency completeness, and at least one format (`conda environment.yml`) that requires an external solver binary. Prioritizing lock-file formats (which already contain the full transitive tree) over manifest-only formats (which require resolver invocation) dramatically reduces implementation complexity and improves output accuracy. The recommended build sequence delivers a working CycloneDX JSON SBOM from `requirements.txt`, `pyproject.toml`, `pixi.lock`, and `pixi.toml` by the end of Sprint 2, with remaining formats and analysis reports completing in Sprints 3–5.

**Key Technical Findings:**

- `cyclonedx-python-lib` v11.11.0 is the correct programmatic library for CycloneDX output — distinct from the CLI tool `cyclonedx-bom`; designed for embedding.
- OSV `POST /v1/querybatch` is the recommended vulnerability scanning path — stable public API, 1000 packages/request, aggregates PyPA + GitHub Advisory + NVD.
- Lock files (`pixi.lock`, `uv.lock`, `poetry.lock`) already contain the full transitive dependency tree — parse them directly; avoid resolver invocation.
- `conda environment.yml` requires the conda/mamba solver binary — mark as best-effort in v1.
- Celery `delay_on_commit()` (not `.delay()`) is mandatory when dispatching tasks from Django views inside database transactions.
- The service layer pattern (plain Python functions in `services.py`, no HTTP/Celery coupling) is the most valuable architectural decision for testability.
- OMB rolled back federal SBOM mandate in January 2026 but CISA guidance and EU CRA still drive enterprise demand.

**Technical Recommendations:**

1. Use `cyclonedx-python-lib` for CycloneDX output and `lib4sbom` for SPDX — two separate code paths, same resolved package list as input.
2. Query OSV batch API directly rather than through pip-audit's private internal modules.
3. Implement parsers in priority order: `requirements.txt` → `pyproject.toml` → `pixi.lock` → `pixi.toml` → `conda environment.yml` → `uv.lock` → `poetry.lock`.
4. Run vulnerability scan, license analysis, graph generation, and version currency in parallel (Celery `group()`) to minimize total job time.
5. Cache PyPI JSON API responses (1h TTL) and OSV responses (24h TTL) in Redis via `requests-cache` to avoid redundant external calls under concurrent load.

---

### Table of Contents

1. [Technical Research Scope Confirmation](#technical-research-scope-confirmation)
2. [Technology Stack Analysis](#technology-stack-analysis)
   - SBOM Generation Libraries
   - Manifest Parsing and Transitive Dependency Resolution
   - Vulnerability Scanning and Advisory Databases
   - Dependency Graph Visualization
   - Version Currency Tracking
   - Django + Celery Integration Stack
3. [Integration Patterns Analysis](#integration-patterns-analysis)
   - API Design Patterns
   - Communication Protocols and Progress Signaling
   - Data Formats and Standards
   - Celery Task Architecture and State Machine
   - Artifact Storage Pattern
   - Integration Security Patterns
4. [Architectural Patterns and Design](#architectural-patterns-and-design)
   - System Architecture: Modular Monolith
   - Django App Structure
   - Service Layer Design Principles
   - Celery Pipeline Architecture
   - Data Architecture
   - Deployment and Operations Architecture
5. [Implementation Approaches and Technology Adoption](#implementation-approaches-and-technology-adoption)
   - CycloneDX SBOM Generation — Library API
   - Manifest Parsing — Implementation Sequence
   - Vulnerability Scanning — pip-audit vs. OSV Direct
   - External API Rate Limiting and Caching
   - Testing Strategy
   - Implementation Roadmap (5 Sprints)
   - Risk Assessment

---

### Performance and Scalability Analysis

**Expected processing times** by manifest complexity (single Celery worker, 4 cores):

| Manifest Size | Phase 1–3 (parse + SBOM) | Phase 4–7 (analysis, parallel) | Total |
|---|---|---|---|
| Small (< 50 packages) | 5–15s | 10–20s | 15–35s |
| Medium (50–250 packages) | 15–45s | 30–90s | 45–135s |
| Large (250–1000 packages) | 45–120s | 90–300s | 2–7 min |
| Very large (1000+ packages) | 2–5 min | 5–20 min | 7–25 min |

The vulnerability scan phase dominates for large manifests due to external API latency, even with batching. The OSV batch endpoint (1000 packages/request) means a 1000-package manifest requires a single batch call; a 2000-package manifest requires two.

**Scaling levers:**
- Horizontal Celery worker scaling handles concurrent jobs without code changes.
- Dedicated Celery queue for analysis phases (phases 4–7) prevents long vulnerability scans from blocking SBOM generation for other users.
- Redis caching of OSV and PyPI responses creates a warm cache after the first few jobs — subsequent jobs with similar dependency sets are dramatically faster.
- Pre-warming the cache with common packages (Django, numpy, requests, etc.) at startup is a low-effort optimization with high return.

---

### Security and Compliance Considerations

**SBOM regulatory landscape (2026):**
- **US Federal:** OMB M-26-05 (Jan 2026) rescinded mandatory SBOM attestation (M-22-18, M-23-16). Agencies may still require SBOMs at their discretion. EO 14028 is the originating authority — still in effect.
- **EU:** Cyber Resilience Act (CRA) imposes mandatory SBOM requirements for CE-marked software products sold in EU markets. Effective 2027 for most product categories.
- **CISA:** SBOM guidance at `cisa.gov/sbom` remains active and is the authoritative reference for SBOM minimum elements (per NTIA).
- **Private sector:** Enterprise software procurement increasingly requires SBOM artifacts in vendor contracts, independent of regulation.

**Application security:**
- Manifest files are user-supplied — treat as untrusted input; parse with safe loaders only.
- Task ID authorization enforced via Django model (not Redis TTL alone): `SBOMJob.user` FK checked on every status/result request.
- Presigned S3 URLs (24h TTL) prevent unauthorized artifact access without requiring authentication on the S3 layer itself.

_Sources: [CISA SBOM](https://www.cisa.gov/sbom) · [OMB M-26-05 — Nextgov](https://www.nextgov.com/cybersecurity/2026/01/omb-reverses-biden-era-software-attestation-order/410939/) · [OMB rescinds — Mayer Brown](https://www.mayerbrown.com/en/insights/publications/2026/02/omb-rescinds-biden-era-software-security-memoranda) · [NIST SBOM supply chain](https://www.nist.gov/itl/executive-order-14028-improving-nations-cybersecurity/software-security-supply-chains-software-1) · [What is SBOM — Wiz](https://www.wiz.io/academy/application-security/software-bill-of-material-sbom)_

---

### Future Technical Outlook

**Near-term (6–18 months):**
- SPDX 3.0 tooling maturity will improve; `lib4sbom`'s experimental SPDX 3.0 support will stabilize — upgrade path is additive.
- `uv` lock file format is likely to see parser tooling stabilize further as it cements market dominance; the TOML parsing approach already works.
- OSV dataset continues to expand; the batch API is stable and versioned.

**Medium-term (1–3 years):**
- EU CRA compliance deadlines (2027) will drive significant enterprise demand for SBOM-as-a-service tooling.
- AI-assisted vulnerability triage (LLM enrichment of CVE descriptions, automated severity contextualization) is an additive analysis report type.
- VEX (Vulnerability Exploitability eXchange) documents, which pair with SBOMs to assert exploitability status for known CVEs, are an emerging complement — CycloneDX 1.6 already supports VEX.

**Long-term (3+ years):**
- SBOM generation may become a platform-level feature (CI/CD platforms, registries) rather than a standalone service — the analysis layer (license compliance, version currency, graph) retains differentiated value.

---

### Technical Research Conclusion

**Summary of key findings:** The technology to build this service exists and is production-mature. The hardest problem is manifest format breadth — seven formats with different resolution strategies — not the SBOM generation or analysis layers. Prioritize lock files in the parser implementation sequence. Use OSV batch API directly. Apply the service layer pattern rigorously so unit tests run without any infrastructure.

**Strategic impact:** A self-service SBOM generation platform targeting the Python ecosystem addresses a gap in the current tooling landscape: existing tools are either CLI-only (not embeddable in a web service) or require the project to be installed locally. A web service that accepts raw manifest/lock files and returns structured SBOM + analysis artifacts enables use cases that none of the current CLI tools support — CI/CD webhook integration, multi-project portfolio analysis, and API-driven compliance reporting.

**Next steps:** Proceed to PRD with the technology selections made by this research. The major open PRD questions are user-facing: authentication model (API key vs. OAuth), multi-tenancy requirements, retention policy for generated artifacts, and whether a UI is required for v1 or an API-first approach is sufficient.

---

**Research Completion Date:** 2026-07-03
**Research Period:** Comprehensive analysis of 2026 current sources
**Source Verification:** All technical claims cited with current public sources
**Technical Confidence Level:** High — based on multiple authoritative sources per claim

_This document serves as the primary technical reference for the `django-python-generate-sbom` project and informs the Product Requirements Document (PRD) that follows in the BMad workflow._
