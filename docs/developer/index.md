# Developer Documentation

This section is for people working **on** the project — contributors, maintainers,
and anyone extending the backend or frontend.

- **[Architecture](architecture.md)** — the layered modular monolith, the async
  pipeline, and the invariants that keep it consistent.
- **[Local Development](setup.md)** — get the full stack running with pixi and
  Docker Compose.
- **[Project Layout](project-layout.md)** — where everything lives in the monorepo.
- **[SBOM Pipeline](pipeline.md)** — the eight-phase Celery pipeline, phase by phase.
- **[Data Model](data-model.md)** — the core Django models and how they relate.
- **[Testing](testing.md)** — the unit/integration split and the `pixi run ci` gate.
- **[Code Reference](code-reference.md)** — API docs generated from the backend
  docstrings.

## The 30-second overview

`django-python-generate-sbom` is a **Django + DRF backend**, a **React/Vite SPA**
frontend, and a **Celery** worker fleet, all managed as one project by a **pixi**
umbrella toolchain. A user uploads a Python dependency manifest; an asynchronous
pipeline resolves the dependency tree, generates a CycloneDX SBOM, and enriches it
with vulnerability, license, and version-currency analysis. Results
are read back through the REST API and rendered in the SPA.

Supporting services are **PostgreSQL** (relational data), **Redis** (the Celery
broker/result backend), and **MinIO/S3** (artifact blob storage). See
[Architecture](architecture.md) for how these fit together.
