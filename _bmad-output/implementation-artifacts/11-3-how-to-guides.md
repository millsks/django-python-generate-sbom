# Story 11.3: How-To Guides

Status: review

## Story

As a user,
I want short task-focused how-to pages,
so that I can quickly accomplish a specific goal without reading the whole guide.

## Acceptance Criteria

1. The How-To section provides concise, task-oriented recipes including at least: generate an SBOM from a `requirements.txt` / `pyproject.toml` / lockfile; interpret the vulnerability report; check license compliance; see which dependencies are outdated; export a report to Excel; create and use an API key; invite a member / switch organizations (FR-DOC3).
2. Each how-to is a focused `goal → steps → result` page, cross-linked to the relevant User Guide section, and added to the `mkdocs.yml` nav under **How-To**.

## Tasks / Subtasks

- [x] Author the seven required how-to recipes under `docs/how-to/`
- [x] Rewrite `docs/how-to/index.md` as a linked overview (replace the placeholder)
- [x] Expand only the **How-To** nav section in `mkdocs.yml`
- [x] Cross-link each recipe to the User Guide section and to related how-tos
- [x] `pixi run docs-build` (strict) and `pixi run ci` green

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Seven recipes authored, each `goal → numbered steps → result`, grounded in the real app: supported manifest formats (`requirements.txt`, `pyproject.toml`, `pixi.lock`, `pixi.toml`, `environment.yml`) from `manifests/detection.py`; the results tabs; the per-tab / Overview "export all" Excel actions; the `Authorization: Api-Key <key>` header and `/api/v1/` base from `users/authentication.py` + `config/urls.py`; the org switcher / `/members` admin flow; app routes (`/upload`, `/results/<task-id>`, `/history`, `/keys`, `/members`).
- The API-key recipe points to the live Swagger UI at `/api/docs/` (Story 11.9) for the full endpoint catalog rather than duplicating it.
- **Cross-links to the User Guide target `../user-guide/index.md` (the section landing) on purpose**: Story 11.2's detailed sub-pages don't exist yet, and `mkdocs build --strict` fails on links to missing pages. When 11.2 lands, these can be deepened to specific pages.
- Scope kept to `docs/how-to/**`, the How-To nav block in `mkdocs.yml`, and this story file — no other nav entries, plugins, or subtrees touched.

### File List

- `docs/how-to/index.md` (rewritten)
- `docs/how-to/generate-sbom.md` (new)
- `docs/how-to/interpret-vulnerabilities.md` (new)
- `docs/how-to/check-license-compliance.md` (new)
- `docs/how-to/find-outdated-dependencies.md` (new)
- `docs/how-to/export-to-excel.md` (new)
- `docs/how-to/manage-api-keys.md` (new)
- `docs/how-to/manage-organization.md` (new)
- `mkdocs.yml` (How-To nav section expanded)
