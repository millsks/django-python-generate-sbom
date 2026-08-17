# Story 21.20: Architecture Reconciliation

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.19**. Documentation-only — no code changes. Follows the precedent of
> Story 14.2 (architecture reconciliation).

## Story

As an architect,
I want the architecture spine to describe the system as it now is,
so that future stories are not planned against decisions this epic reversed.

## Acceptance Criteria

1. **AD-5 is superseded by AD-15.**
   Given AD-5 mandates a React SPA with "no Django template coupling" — the exact opposite of what now exists —
   when the spine is reconciled, then AD-5 is marked **superseded** and **AD-15** replaces it, stating that the
   web UI is server-rendered Django templates whose views call the service layer directly and never call
   `/api/v1/` over HTTP (**AD-1**, **AD-3**), while `/api/v1/` remains the programmatic contract (**AD-8**).
2. **AD-16 and AD-17 are recorded.**
   Given the app structure and user identity both changed, when the spine is reconciled, then **AD-16** records
   the single `src/django_apps/inventory/` app — installed and imported **unqualified** as `inventory` from a
   `src/django_apps/` path root that carries **no `__init__.py`**, with app-internal templates and static — and
   **AD-17** records that app code depends on `settings.AUTH_USER_MODEL`/`get_user_model()` with the concrete
   `User` owned by `src/django_service/users/`, noting that the setting's **value** (`users.User`) is unchanged.
3. **AD-13 is amended for the `src/` layout.**
   Given AD-13 describes `backend/` and `frontend/` as project-root peers, when it is amended, then it
   describes the `src/{config,django_service,django_apps}` + root-`tests/` layout adopted from the
   `django-15-factor-base` reference application, records `APPS_DIR = BASE_DIR / "src" / "django_service"` as
   the driver of `TEMPLATES["DIRS"]`/`STATICFILES_DIRS`/`MEDIA_ROOT`, and names
   `[tool.hatch.build.targets.wheel] sources` as the **single** import-root declaration site.
4. **The Stack table and Source tree match reality.**
   Given the Stack table lists React, @mui/material, Vite, and the retired Cytoscape packages, when it is
   updated, then those entries are removed, django-crispy-forms, crispy-bootstrap5, django-tables2,
   django-filter, htmx, Bootstrap, and openpyxl are added at their pinned versions, and the **Source tree**
   section is rewritten.
5. **The capability map is repointed.**
   Given the Capability → Architecture Map points F6 and F7 at `frontend/`, when it is updated, then both point
   at the Django app and cite AD-15/AD-16, and the **Deferred** entry for "Frontend state management" is
   removed as moot.
6. **Deferred pluggability is recorded, not lost.**
   Given pluggability into a `django-15-factor-base` platform is explicit future intent, when the spine is
   reconciled, then a **Deferred** entry records the four known gaps — global `DEFAULT_AUTHENTICATION_CLASSES`
   (`base.py:52`) and `DEFAULT_PERMISSION_CLASSES` (`:55`), `config`'s direct import of the app's
   `configure_structlog` (`:12`), and the app-owned `STORAGES["default"]` backend (`production.py:42`) —
   together with the contribution module, `component.toml`, `src/config/startup/` composition,
   `django_service.__api_version__`, navigation registry, and adoption gate test not implemented.

## Tasks / Subtasks

- [ ] **Task 1 — Supersede AD-5, add AD-15 (AC: #1)**.
- [ ] **Task 2 — Add AD-16, AD-17 (AC: #2)**.
- [ ] **Task 3 — Amend AD-13 (AC: #3)**.
- [ ] **Task 4 — Stack table + Source tree (AC: #4)**.
- [ ] **Task 5 — Capability map + Deferred cleanup (AC: #5)**.
- [ ] **Task 6 — Deferred pluggability entry (AC: #6)**.

## Dev Notes

### Grounded facts (verified)

- Spine: `_bmad-output/planning-artifacts/architecture/architecture-django-python-generate-sbom-2026-07-03/ARCHITECTURE-SPINE.md`
  — AD-5 at `:65`, AD-13 at `:122`, Dependency Direction at `:143`, Consistency Conventions at `:180`, Stack at
  `:204`, Structural Seed at `:238`, Source tree at `:325`, Capability map at `:367`, Deferred at `:382`.
- AD-5's current text explicitly forbids what this epic built: "No Django template tag, context processor, or
  `{% block %}` passes business data to React components" and mandates `STATICFILES_DIRS` include
  `../frontend/dist/`.
- The Stack table lists React 19.2.7, @mui/material 9.1.2, Vite 8.1.3, cytoscape 3.34.0, react-cytoscapejs
  2.0.0, cytoscape-dagre 4.0.0 — the three Cytoscape entries are **already stale** (Story 20.1 retired the
  dependency graph) and should go with the rest.
- The Deferred section's "Frontend state management — Redux vs Zustand vs React Query" entry is moot.
- Precedent: Story 14.2 (`14-2-architecture-reconciliation.md`) did this same job for Epics 1–13.

### Also worth catching while in here

- **AD-9** (graph API shape) and the NetworkX/pygraphviz Stack entries relate to the dependency graph retired by
  Story 20.1. If Story 20.1 did not already reconcile them, note it — but do not expand this story's scope to
  fix Epic 20's leftovers without flagging it.
- The **Deferred** entry "WebSocket / Django Channels — polling architecture (AD-5) does not block this
  addition" references AD-5 and needs its citation updated to AD-15.

### Testing standards

Documentation-only; the gate is `pixi run ci` (unchanged) plus a read-through confirming no remaining reference
to `frontend/` or the SPA in the spine.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.20: Architecture Reconciliation]
- `ARCHITECTURE-SPINE.md`, `solution-design.md`, `one-pager.md`, `architecture-diagrams.html`.
- Precedent: `14-2-architecture-reconciliation.md`.
- Upstream: `21-19-retire-react-spa-and-node-toolchain.md`.

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
