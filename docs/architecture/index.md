# Architecture

Design records: what the system is, why it is shaped that way, and which decisions are
still open.

- **[Technology Stack Rationale](technology-stack-rationale.md)** — why each major
  technology was chosen, the alternatives weighed against it, and the conditions under
  which the decision should be reopened. Includes a detailed assessment of **Celery
  vs. Kedro** for the SBOM pipeline.

## Where the authoritative record lives

The binding design record is the **architecture spine** at
`_bmad-output/planning-artifacts/architecture/…/ARCHITECTURE-SPINE.md`, which carries the
numbered decisions (AD-1 … AD-21) the codebase is built against. Pages in this section
summarise and explain it; **when the two disagree, the spine wins.**

Day-to-day design orientation currently lives in the
[Developer](../developer/index.md) section — [Architecture](../developer/architecture.md),
[Tech Stack](../developer/tech-stack.md), [Data Model](../developer/data-model.md),
[SBOM Pipeline](../developer/pipeline.md), and
[Project Layout](../developer/project-layout.md).
