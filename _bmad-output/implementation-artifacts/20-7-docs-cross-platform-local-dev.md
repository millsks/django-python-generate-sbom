# Story 20.7: Docs — Cross-Platform Local Development

Status: review

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

- [x] **Task 1 — Containerless setup (AC: #1, #3)** — Update `docs/developer/setup.md` with macOS + Windows
  containerless steps (`pixi install` → `pixi run dev`), the local settings module, and the Windows pool /
  `runserver` / portable-path notes.
- [x] **Task 2 — Environment matrix (AC: #2)** — Add an environment-matrix table (local vs. OCP/prod) covering
  DB, storage, Celery broker+backend, containerization, web server, and settings module.
- [x] **Task 3 — Graph cleanup sweep (AC: #4)** — Confirm no residual Graphviz/pygraphviz prerequisite or
  dependency-graph mention remains in the developer docs (paired with Story 20.1's docs edits).
- [x] **Task 4 — Build (AC: #5)** — Run the docs build/link check; fix any broken nav/links; confirm green.

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

claude-opus-4-8[1m]

### Debug Log References

- `pixi run docs-build` (`mkdocs build --strict`) — clean, no broken links/nav from the edits.
- `pixi run ci` — exit 0 (precommit, build, check, lint, fmt-check, security, cov, fe-lint, fe-typecheck,
  fe-cov, fe-build, docs-build all green). Code suites unchanged; only docs edited.

### Completion Notes List

- Rewrote `docs/developer/setup.md` to make containerless `pixi run dev` the primary local flow on both macOS
  (osx-arm64) and Windows (win-64): `pixi install` → `cp .env.local.example .env` → `pixi run migrate` →
  `pixi run dev` (honcho/Procfile launches `runserver` web + real Celery worker + beat). Documented
  `config.settings.local` with SQLite + FileSystemStorage + `filesystem://` broker + `django-db` result
  backend, and that no Docker/Postgres/Redis/MinIO is needed locally (AC #1).
- Added a Windows-specifics section: `--pool=solo` worker (prefork is Unix-only; pixi selects it per platform
  via the `[target.win-64.tasks.worker]` override), `runserver` instead of gunicorn (Unix-only), and the
  portable git-ignored `backend/.celery/` broker + `backend/.celery/celerybeat-schedule` beat paths (AC #3).
- Added an environment matrix table (local containerless vs. OCP/prod) covering settings module, DB, storage,
  Celery broker + result backend, web server, worker pool, and containers; cross-linked the OpenShift guide
  and migration guide (AC #2). Verified every documented pixi task exists in `pixi.toml`.
- Kept the Docker Compose path documented as the optional prod-parity stack (AC #1 — primary flow is
  containerless).
- Graph cleanup sweep (AC #4): confirmed no residual Graphviz/pygraphviz/dependency-graph references remain in
  `docs/` (Story 20.1 already removed them) — nothing to strip.
- Updated `docs/developer/index.md` to describe local dev as containerless-first with Docker Compose as the
  optional prod-parity path.
- Docs build clean under `--strict` (AC #5).

### File List

- `docs/developer/setup.md` (rewritten: containerless-first workflow, Windows specifics, environment matrix)
- `docs/developer/index.md` (containerless-first summary line)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (20.7 → review; 20.6 → done)
- `_bmad-output/implementation-artifacts/20-7-docs-cross-platform-local-dev.md` (status, tasks, Dev Agent Record)
