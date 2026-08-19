# Architecture

What the system is, why it is shaped that way, and which decisions are still open.

- **[Overview](architecture.md)** — the layered modular monolith, the async pipeline, and
  the invariants that keep it consistent.
- **[Technology Stack Rationale](technology-stack-rationale.md)** — why each major
  technology was chosen, the alternatives weighed against it, and when the decision should
  be reopened. Includes a detailed **Celery vs. Kedro** assessment.
- **[Tech Stack](tech-stack.md)** — the frameworks and libraries, layer by layer, with the
  version floors they are pinned against.
- **[Project Layout](project-layout.md)** — the `src/` tree, and the rules that keep the
  app importable as `inventory` from both a checkout and a built wheel.
- **[SBOM Pipeline](pipeline.md)** — the eight-phase Celery pipeline, phase by phase.
- **[Data Model](data-model.md)** — the core Django models and how they relate.

## Where the authoritative record lives

The binding design record is the **architecture spine** at
`_bmad-output/planning-artifacts/architecture/…/ARCHITECTURE-SPINE.md`, which carries the
numbered decisions (AD-1 … AD-21) the codebase is built against. The pages here summarise
and explain it; **when the two disagree, the spine wins.**

## This section vs. Developer

These pages describe **what the system is** — they change when a decision changes. The
[Developer](../developer/index.md) section covers **how to work on it**: running the stack
locally, the test suite and the CI gate, and a file-by-file reference for the `inventory`
app.
