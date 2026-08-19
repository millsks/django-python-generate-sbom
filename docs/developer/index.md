# Developer Documentation

This section is for people working **on** the project — contributors, maintainers,
and anyone extending the application.

- **[Local Development](setup.md)** — get the stack running containerless with
  `pixi run dev` on macOS or Windows (Docker Compose is the optional prod-parity
  path).
- **[Inventory App Reference](inventory-app-reference.md)** — a file-by-file tour of the
  reusable `inventory` app: what each module does, the invariant it carries, and which of
  its neighbours it may import.
- **[Testing](testing.md)** — the unit/integration split and the `pixi run ci` gate.
- **[Code Reference](code-reference.md)** — API docs generated from the Python
  docstrings.

Design records — what the system *is*, rather than how to work on it — live in
**[Architecture](../architecture/index.md)**:
[Overview](../architecture/architecture.md),
[Technology Stack Rationale](../architecture/technology-stack-rationale.md),
[Tech Stack](../architecture/tech-stack.md),
[Project Layout](../architecture/project-layout.md),
[SBOM Pipeline](../architecture/pipeline.md), and
[Data Model](../architecture/data-model.md).

## The 30-second overview

**FABRIC** is a **Django + DRF** application with a
**server-rendered UI** and a **Celery** worker fleet, all managed as one project by a
**pixi** umbrella toolchain — one language, one environment, one runner. A user uploads a
Python dependency manifest; an asynchronous pipeline resolves the dependency tree,
generates a CycloneDX SBOM, and enriches it with vulnerability, license, and
version-currency analysis. Results are rendered by Django templates, and the same data is
available to scripted clients through the versioned REST API.

Supporting services are **PostgreSQL** (relational data), **Redis** (the Celery
broker/result backend), and **MinIO/S3** (artifact blob storage). See
[Architecture](../architecture/architecture.md) for how these fit together.
