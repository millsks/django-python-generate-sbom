# Story 11.4: Developer Documentation

Status: review

## Story

As a contributor,
I want developer documentation of the architecture and codebase,
so that I can set up locally and understand how the system fits together.

## Acceptance Criteria

1. Developer section covers architecture overview, local dev setup (`pixi install`, Docker Compose, running the stack), project layout, and the testing model (unit vs. integration, `pixi run ci`) (FR-DOC4).
2. The phased Celery SBOM pipeline and the key data models are explained, drawing on the BMad architecture spine.
3. `mkdocstrings[python]` auto-renders a backend code reference into the site (markdown pages with `:::` handlers), so docstrings surface in the docs.
4. Developer pages added to the `mkdocs.yml` nav under **Developer**.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Wrote the Developer section under `docs/developer/`: `index.md` (overview + section
  index), `architecture.md` (paradigm + containers + the load-bearing ADs +
  dependency direction), `setup.md` (pixi + Docker Compose + per-process tasks +
  settings split + task table), `project-layout.md` (monorepo tree + conventions),
  `pipeline.md` (the eight-phase Celery canvas, two queues, keys-not-blobs, status &
  failure handling), `data-model.md` (core models + a mermaid ER diagram), and
  `testing.md` (unit/integration split + the `pixi run ci` gate steps).
- Grounded everything in the real code and the architecture spine
  (`ARCHITECTURE-SPINE.md`), citing AD-1..AD-13 where they bind behavior.
- **mkdocstrings code reference:** enabled the `mkdocstrings` plugin in `mkdocs.yml`
  with the Python (griffe) handler and `paths: [backend]`. Because griffe renders
  **statically** from source, no `DJANGO_SETTINGS_MODULE`/`django.setup()` is needed
  and `--strict` stays clean — no runtime import of Django occurs. Scoped
  `docs/developer/code-reference.md` to the pure service layer + shared abstractions
  (`common.storage`, `common.logging`, `analysis.services.versions`,
  `analysis.services.parselmouth`, `analysis.services.http`), which resolve cleanly
  under `--strict` (verified: 42 documented symbols rendered).
- Expanded the `mkdocs.yml` **Developer** nav section to list all pages; left the
  other nav sections untouched to avoid conflicts with sibling content stories.
- `pixi run docs-build` (`mkdocs build --strict`) passes with mkdocstrings enabled;
  `pixi run ci` exits 0.

### File List

- `docs/developer/index.md`
- `docs/developer/architecture.md`
- `docs/developer/setup.md`
- `docs/developer/project-layout.md`
- `docs/developer/pipeline.md`
- `docs/developer/data-model.md`
- `docs/developer/testing.md`
- `docs/developer/code-reference.md`
- `mkdocs.yml` (enabled mkdocstrings plugin; expanded Developer nav)
- `_bmad-output/implementation-artifacts/11-4-developer-documentation.md`
