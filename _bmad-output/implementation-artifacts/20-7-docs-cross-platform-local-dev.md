# Story 20.7: Docs — Cross-Platform Local Development

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **last in Epic 20**, after Stories 20.1–20.6 land — the docs describe the final,
> merged containerless workflow.

## Story

As a new contributor,
I want the developer setup docs to cover containerless local dev on both macOS and Windows plus the
environment matrix,
so that I can run the stack with no Docker on either OS and understand how local differs from OCP/prod.

## Acceptance Criteria

1. **Containerless setup for macOS and Windows.**
   Given `docs/developer/setup.md` documents the current setup, when this story lands, then it documents the
   containerless local workflow for **both** macOS (osx-arm64) and Windows (win-64): `pixi install`, then
   `pixi run dev` (web `runserver` + real Celery worker + beat via honcho/Procfile), using
   `config.settings.local` with SQLite + filesystem storage and the Kombu `filesystem://` broker + DB result
   backend — **no Docker, Postgres, Redis, or MinIO required locally**.
2. **Environment matrix documented.**
   Given local and OCP/prod diverge, when the docs are updated, then a clear **environment matrix** states:
   **local** = SQLite / filesystem storage / `filesystem://` broker + DB result backend / no containers /
   `runserver`; **OCP/prod** = enterprise **PostgreSQL** / enterprise **S3** / enterprise **Redis** (broker +
   result backend) / containerized (single umbrella image) / gunicorn. It notes which settings module drives
   each (`config.settings.local` vs `config.settings.production`).
3. **Windows specifics called out.**
   Given the Windows-specific differences, when the docs are updated, then they explain the Windows worker pool
   (`--pool=solo`/`threads` vs. prefork), that gunicorn is not used locally (`runserver` instead), and the
   portable git-ignored `backend/.celery/` broker/beat paths — so a Windows developer hits no surprises.
4. **Dependency-graph references removed from docs.**
   Given Story 20.1 retired the dependency graph, when this docs story lands, then the developer setup/docs
   contain **no** residual dependency-graph, pygraphviz, or graphviz setup instructions (e.g. no "install
   Graphviz" prerequisite), consistent with the doc cleanup in Story 20.1.
5. **Docs build clean.**
   Given the MkDocs Material site, when the docs are updated, then the docs build/link-check (the project's
   docs task) passes with the new/edited pages and nav entries, and no broken links to removed graph pages
   remain.

## Tasks / Subtasks

- [ ] **Task 1 — Containerless setup (AC: #1, #3)** — Update `docs/developer/setup.md` with macOS + Windows
  containerless steps (`pixi install` → `pixi run dev`), the local settings module, and the Windows pool /
  `runserver` / portable-path notes.
- [ ] **Task 2 — Environment matrix (AC: #2)** — Add an environment-matrix table (local vs. OCP/prod) covering
  DB, storage, Celery broker+backend, containerization, web server, and settings module.
- [ ] **Task 3 — Graph cleanup sweep (AC: #4)** — Confirm no residual Graphviz/pygraphviz prerequisite or
  dependency-graph mention remains in the developer docs (paired with Story 20.1's docs edits).
- [ ] **Task 4 — Build (AC: #5)** — Run the docs build/link check; fix any broken nav/links; confirm green.

## Dev Notes

### Grounded facts (verified)

- Local base defaults (no rewrite): `base.py` SQLite (L108–110), FileSystemStorage (L130–137); Celery becomes
  `filesystem://` + DB result backend in local dev (Story 20.4). `config.settings.local` is the containerless
  module (Story 20.3).
- OCP/prod (Epic 19): enterprise PostgreSQL / Redis / S3, containerized umbrella image, gunicorn `web`,
  `config.settings.production`. The matrix should mirror Epic 19's fixed decisions.
- The dependency graph (and its Graphviz prerequisite) is retired in Story 20.1 — the developer docs must not
  reintroduce it.

### Content pointers

- Primary page: `docs/developer/setup.md`. Related developer pages touched by Story 20.1's cleanup:
  `docs/developer/index.md`, `docs/developer/project-layout.md`, `docs/developer/pipeline.md`,
  `docs/developer/data-model.md` (report count). This story focuses on the **setup + matrix** narrative; the
  graph-removal edits are Story 20.1's, and this story only sweeps for residue.

### Testing standards

- No unit-test surface — this is documentation. Verification is a clean docs build/link-check and a manual
  read-through confirming the two-OS containerless workflow and the environment matrix are correct.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.7: Docs — Cross-Platform Local Development]
- `docs/developer/setup.md` (primary), `docs/developer/{index,project-layout,pipeline,data-model}.md`.
- Upstream: all of Stories 20.1–20.6 (this documents the merged result). Cross-refs: Epic 19 (OCP/prod side of
  the matrix), Stories 20.3/20.4/20.5 (local settings, worker, `pixi run dev`).

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
