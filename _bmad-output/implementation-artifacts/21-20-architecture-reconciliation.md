---
baseline_commit: e137169
---

# Story 21.20: Architecture Reconciliation

Status: review

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

- [x] **Task 1 — Supersede AD-5, add AD-15 (AC: #1)**.
- [x] **Task 2 — Add AD-16, AD-17 (AC: #2)**.
- [x] **Task 3 — Amend AD-13 (AC: #3)**.
- [x] **Task 4 — Stack table + Source tree (AC: #4)**.
- [x] **Task 5 — Capability map + Deferred cleanup (AC: #5)**.
- [x] **Task 6 — Deferred pluggability entry (AC: #6)**.

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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**, unchanged: **806 passed**, coverage **96.72%**. Documentation-only,
  so no code or test changes.
- Spine invariants now: AD-1 … AD-14 plus **AD-15** (server-rendered UI), **AD-16** (single
  reusable app), **AD-17** (user model reference). AD-5 marked **SUPERSEDED**; AD-13 marked
  **AMENDED**.
- Read-through (AC gate): `grep -n 'frontend|SPA|React|Vite|MUI'` over the spine returns only
  the deliberate historical records in AD-5, AD-13's amendment note, AD-9 (flagged below), and
  one back-pointer in AD-14 naming the `AdminRoute` the mixin replaced.
- Versions confirmed against the installed environment, not the story text: crispy-forms 2.6,
  crispy-bootstrap5 2026.3, django-tables2 3.0.0, django-filter 26.1, openpyxl 3.1.5,
  Bootstrap 5.3.8, Bootstrap Icons 1.13.1, htmx 2.0.8.

### Completion Notes List

**AD-5 is superseded, not deleted, and it says why it was reversed.** A reader arriving at a
decision that mandates the opposite of what exists needs to know that was deliberate. So AD-5
keeps its original rule under a "no longer in force" heading plus a short reason — the SPA
duplicated in TypeScript the access control, org scoping, and report rendering the service layer
already owned. AD-15 is written to preserve the *outcome* AD-5 protected (no business logic in
the presentation layer, one contract for programmatic clients) rather than to reverse it wholesale,
which is the honest description of what the epic did.

**AD-15 forbids the mistake that would otherwise be tempting.** The obvious way to build a
server-rendered UI on top of an existing REST API is to have the page views call it — which is an
in-process HTTP hop, forbidden by AD-1, and would silently make the API a private backend. The
rule states that page views and DRF views are **peers** on the service layer, and records the
shared-service pattern the epic actually used (`submit_job`, `read_report`) as the mechanism that
keeps the HTML and JSON paths from diverging.

**Three traps that cost real debugging time in this epic are now written down where the next
person will hit them**, rather than living only in commit messages: the hatchling `sources`
array-vs-mapping shadowing (AD-16), management commands loading only from the app root (AD-16),
and `Meta.order_by` naming a column rather than an accessor (Consistency Conventions). Each
produces **no error** — a broken wheel with a green test suite, a silently missing command, an
unsorted table — which is exactly why a convention entry is worth more than a fix.

**`user_ref()` is documented as deliberately-not-dead code.** It reads like a no-op and is the
seam that keeps the app off the concrete `User`; AD-17 says so explicitly, because the obvious
tidy-up re-introduces the single hardest coupling to remove later.

**Two ACs asserted things that are not true of the code, and I recorded what is.**
1. AC #3 says `APPS_DIR` drives `MEDIA_ROOT`. It does not — `MEDIA_ROOT` and `STATIC_ROOT` hang
   off `BASE_DIR` (`base.py:174,180`); `APPS_DIR` drives `TEMPLATES["DIRS"]` and
   `STATICFILES_DIRS` only. AD-13 states the true split and says why (deployment paths vs
   host-package assets).
2. AC #6 cites the violations at `base.py:52`/`:55`/`:12`. They are at `:81`, `:85`, and `:20`;
   the line numbers moved when the tree became a `src/` layout. The Deferred entry names the
   settings and symbols rather than line numbers, so it cannot rot the same way again.

**AD-2 was tightened, not merely reworded.** It said the Web UI returns `403` for cross-org
access while the API returns `404`. The server-rendered implementation returns `404` for both
via `get_org_scoped_object_or_404`, which folds the org filter into the query — and that is the
better rule, because a `403`-vs-`404` difference confirms that an object the caller cannot see
exists. The change is called out inline rather than quietly swapped, since it reverses a stated
UX preference from FR-6.8.

**AD-9 and the graph stack entries are stale, and I left AD-9 alone on purpose.** Story 20.1
retired the dependency graph — `analysis/services/graph.py` is gone and NetworkX, pygraphviz, and
the three Cytoscape packages are no longer dependencies — but 20.1 never touched the spine, and
its story file does not mention it. The Cytoscape rows came out because AC #4 names them
explicitly; **AD-9 still describes a graph API that no longer exists**, and rewriting an Epic 20
decision from an Epic 21 story would hide the gap rather than close it. It is recorded in
**Deferred** and flagged for a correct-course pass on Epic 20. The Dev Notes asked for exactly
this.

**The companion documents are not reconciled, and now say so.** The six ACs name
`ARCHITECTURE-SPINE.md` and no other file, but `solution-design.md` (40 SPA references over 825
lines, including a whole "Frontend Architecture" chapter) and `architecture-diagrams.html` (54,
across rendered diagrams) sit in the same directory and would read as current. Rewriting them is
a materially larger job than these ACs describe, so instead each carries a prominent notice
naming what Epic 21 changed and pointing at the spine as authoritative, and
`solution-design.md`'s Design-principles table has its two now-wrong rows struck through. **This
needs its own story** — flagged rather than silently absorbed or silently skipped.

**Still open, unchanged:** the `beat_schedule` maintenance tasks are absent from the Celery
registry (found in 21.1, needs its own bug story).

### File List

**Modified (4)**
- `.../architecture-django-python-generate-sbom-2026-07-03/ARCHITECTURE-SPINE.md` — AD-5
  superseded; AD-15/16/17 added; AD-13 amended; Design Paradigm, AD-2, AD-14, Dependency
  Direction, System containers, Consistency Conventions, Stack, Source tree, Capability map, and
  Deferred all updated
- `.../solution-design.md` — reconciliation notice; two Design-principles rows struck through
- `.../architecture-diagrams.html` — reconciliation banner
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

No code, test, or configuration files were changed.

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Reconciled the architecture spine with what Epic 21 built. AD-5 (React SPA) is marked superseded — kept, with the reason it was reversed — and **AD-15** replaces it: server-rendered Django page views call the service layer directly and never `/api/v1/`, which stays the programmatic contract. Added **AD-16** (one `inventory` app imported unqualified from a non-package path root, with the hatchling `sources` shadowing trap recorded) and **AD-17** (the app depends on `AUTH_USER_MODEL`, never the concrete `User`, whose value is unchanged). Amended **AD-13** for the `src/` layout, naming the hatch `sources` block as the single import-root declaration site. Rewrote the Stack table, Source tree, dependency graph, capability map, and Deferred section, including the four unimplemented pluggability gaps. Two ACs asserted facts the code contradicts (`MEDIA_ROOT` is not `APPS_DIR`-driven; the violation line numbers had moved) — the spine records what is true and the story records the discrepancy. AD-9 and the retired graph stack are stale from Story 20.1 and were deliberately left for an Epic 20 correct-course rather than silently rewritten. `pixi run ci` exit 0, unchanged at 806 tests / 96.72%. |
