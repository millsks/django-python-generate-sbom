# Developer Documentation

This section is for people working **on** the project — contributors, maintainers,
and anyone extending the application.

- **[Architecture](architecture.md)** — the layered modular monolith, the async
  pipeline, and the invariants that keep it consistent.
- **[Tech Stack](tech-stack.md)** — the major frameworks and libraries, layer by
  layer, and why each is here.
- **[Local Development](setup.md)** — get the stack running containerless with
  `pixi run dev` on macOS or Windows (Docker Compose is the optional prod-parity
  path).
- **[Project Layout](project-layout.md)** — where everything lives in the `src/` tree.
- **[SBOM Pipeline](pipeline.md)** — the eight-phase Celery pipeline, phase by phase.
- **[Data Model](data-model.md)** — the core Django models and how they relate.
- **[Testing](testing.md)** — the unit/integration split and the `pixi run ci` gate.
- **[Code Reference](code-reference.md)** — API docs generated from the Python
  docstrings.

## The 30-second overview

**Python Inventory Supply Lens** is a **Django + DRF** application with a
**server-rendered UI** and a **Celery** worker fleet, all managed as one project by a
**pixi** umbrella toolchain — one language, one environment, one runner. A user uploads a
Python dependency manifest; an asynchronous pipeline resolves the dependency tree,
generates a CycloneDX SBOM, and enriches it with vulnerability, license, and
version-currency analysis. Results are rendered by Django templates, and the same data is
available to scripted clients through the versioned REST API.

Supporting services are **PostgreSQL** (relational data), **Redis** (the Celery
broker/result backend), and **MinIO/S3** (artifact blob storage). See
[Architecture](architecture.md) for how these fit together.
