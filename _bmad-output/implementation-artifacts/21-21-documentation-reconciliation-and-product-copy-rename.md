# Story 21.21: Documentation Reconciliation and Product-Copy Rename (L6)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.20**. Carries **rebrand layer L6**. Deliberately runs after the UI
> exists and React is retired, so the docs describe what is actually there. Most of the 154-file "sbom"
> footprint is in this story.

## Story

As a user or contributor,
I want the documentation and all user-facing copy to match the application and its new name,
so that I am not following instructions for a UI that no longer exists, under a name the product no longer
uses.

## Acceptance Criteria

1. **Developer docs describe the new layout and toolchain.**
   Given `docs/developer/project-layout.md`, `architecture.md`, and `setup.md` describe a `backend/` +
   `frontend/` monorepo with npm and Vite, when they are reconciled, then they describe the
   `src/{config,django_service,django_apps}` + root-`tests/` layout, the Node-free toolchain, the
   fresh-database requirement from Story 21.2, and a `pixi run dev` loop with **no `:5173` frontend process**.
2. **User-facing guides match the server-rendered UI.**
   Given the seven `docs/user-guide/` pages and eight `docs/how-to/` pages describe SPA navigation, when they
   are reconciled, then their navigation instructions and any screenshots match the server-rendered UI.
3. **Project meta docs drop the frontend.**
   Given `README.md` and `CONTRIBUTING.md` document the frontend build and its test commands, when they are
   reconciled, then those instructions are removed and the badge set no longer advertises frontend coverage.
4. **The product copy is renamed, but the domain vocabulary is not.**
   Given the product is renamed but still produces SBOMs, when the copy sweep runs, then `mkdocs.yml`
   `site_name` and `site_description` (`:3-4`), the header brand, `README.md`, `CONTRIBUTING.md`,
   `SECURITY.md`, the `docs/` tree, and `presentations/` all use the new product name — **full form "Python
   Inventory Supply Lens"**, **short form "Supply Lens"** per the Story 21.3 convention — while the words
   **"SBOM" and "CycloneDX" are retained wherever they name the artifact or the standard**.
5. **The rename misses nothing silently.**
   Given 154 files contain a case-insensitive "sbom", when the sweep completes, then a documented audit
   accounts for **every remaining occurrence** as either **intentional** (domain term, model name, API path,
   changelog history) or **renamed**, with no unreviewed residue.
6. **The API reference is confirmed unchanged.**
   Given `/api/v1/` did not change in this epic, when the API docs are checked, then they are confirmed
   unchanged, and the docs build (`pixi run docs-build`, `--strict`) passes with no broken links.

## Tasks / Subtasks

- [ ] **Task 1 — Developer docs (AC: #1)** — `project-layout.md`, `architecture.md`, `setup.md`, `testing.md`,
  `pipeline.md`, `code-reference.md`, `index.md`.
- [ ] **Task 2 — User guide + how-to (AC: #2)** — 15 pages; re-shoot screenshots against the new UI.
- [ ] **Task 3 — Project meta (AC: #3)** — `README.md`, `CONTRIBUTING.md`, badges.
- [ ] **Task 4 — Product copy sweep (AC: #4)** — Two name forms, applied per the Story 21.3 convention.
- [ ] **Task 5 — Residue audit (AC: #5)** — Enumerate and classify every remaining "sbom"; record the table.
- [ ] **Task 6 — API docs check + strict build (AC: #6)**.

## Dev Notes

### Grounded facts (verified)

- `docs/` tree: `developer/` (architecture, code-reference, data-model, index, pipeline, project-layout, setup,
  testing), `user-guide/` (7 pages), `how-to/` (8 pages), `api/` (6 pages), `deployment/openshift/` (4 pages),
  `contributing.md`, `index.md`.
- `mkdocs.yml:3-7` — `site_name: django-python-generate-sbom`, `site_description: "Generate and analyze
  CycloneDX SBOMs for Python projects — vulnerabilities, licenses, and version currency."`, plus `site_url`,
  `repo_url`, `repo_name`. **`site_url`/`repo_url`/`repo_name` are layer L5 and stay unchanged** — see Story
  21.22.
- **154 files** contain a case-insensitive "sbom" (excluding `.git`, `node_modules`, `site/`, `dist/`,
  `.pixi/`, `_bmad*`): `docs` 27, `backend/generate_sbom` 36, `backend/tests` 40, `backend/config` 7,
  `frontend/src` 23 (deleted by 21.19), `.github` 1, `presentations` 1.
- `pixi run docs-build` is `mkdocs build --strict`.
- Precedent: Stories 11.11–11.18 did staged documentation reconciliation; 14.1/14.2 did planning-artifact
  reconciliation.

### The distinction that governs the whole sweep

The **app** is renamed; the **artifact** is not. "Generate an SBOM", "CycloneDX SBOM", "SBOM document" all
stay. What changes is the product's name in titles, brands, and prose that previously said "Generate SBOM" as
a proper noun. A blind find-and-replace will break AC #4 — hence the audit in AC #5.

### Watch for

- **`docs/deployment/openshift/` (4 pages)** describes Epic 19, which is unimplemented. Rename copy there, but
  do not "fix" its content to match a deployment that does not exist.
- **`CHANGELOG.md` history is not rewritten** (Story 21.22 AC) — it will legitimately contain the old name.
- **Screenshots** are the slow part. Budget for re-capturing every UI screenshot in `docs/user-guide/` and
  `docs/how-to/`.

### Testing standards

Documentation-only. Gate: `pixi run docs-build --strict` passes, `pixi run ci` exits 0, and the residue audit
table is committed alongside.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.21: Documentation Reconciliation and Product-Copy Rename (L6)]
- `docs/**`, `mkdocs.yml`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `presentations/`.
- Upstream: `21-20-architecture-reconciliation.md`. Sibling: `21-22-distribution-identity-rename.md` (L4).

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
