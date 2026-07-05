# Code Reference

API documentation generated directly from the backend's Google-style docstrings via
[`mkdocstrings`](https://mkdocstrings.github.io/). It is rendered **statically** from
the source (no Django runtime needed), so it always matches the code on this branch.

The reference is scoped to the **service layer** and shared abstractions — the pure,
reusable functions that hold the system's behavior (AD-3). Views, tasks, and models
are documented narratively in [Architecture](architecture.md), the
[Pipeline](pipeline.md), and the [Data Model](data-model.md).

## Shared abstractions (`common`)

::: generate_sbom.common.storage

::: generate_sbom.common.logging

## Analysis services

::: generate_sbom.analysis.services.versions

::: generate_sbom.analysis.services.parselmouth

::: generate_sbom.analysis.services.http
