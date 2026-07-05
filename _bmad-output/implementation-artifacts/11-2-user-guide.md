# Story 11.2: User Guide

Status: review

## Story

As an end user,
I want a guide that walks through using the app,
so that I can register, generate an SBOM, and understand the results without help.

## Acceptance Criteria

1. Covers the full journey in markdown pages: creating an account and organization, logging in and switching orgs, uploading a manifest (supported formats), submitting a job and watching progress, and reading the Results page (FR-DOC2).
2. Each Results tab is explained — Overview, SBOM viewer, Vulnerabilities, Licenses, Dependency Graph (direct vs. transitive), Version Currency (incl. LTS and PyPI/conda-forge latest) — with what each column/badge means.
3. Exporting reports to Excel, downloading the SBOM document, the Job History dashboard, and API key management are each covered.
4. Screenshots (or annotated placeholders) illustrate the key screens; pages are added to the `mkdocs.yml` nav under **User Guide**.

## Tasks / Subtasks

- [x] `docs/user-guide/index.md` — guide overview + map (AC #1)
- [x] `accounts-and-organizations.md` — register, login, org switch, members, logout (AC #1)
- [x] `generating-an-sbom.md` — supported formats, upload form, output formats, submit + progress (AC #1)
- [x] `reading-the-results.md` — all six tabs with column/badge meanings (AC #2)
- [x] `exporting-and-downloading.md` — per-report + Overview Excel export, SBOM download (AC #3)
- [x] `job-history.md` — history dashboard + live status (AC #3)
- [x] `api-keys.md` — create/copy-once/revoke, `Authorization: Api-Key` usage (AC #3)
- [x] Expand the **User Guide** nav section in `mkdocs.yml`; screenshot placeholders per page (AC #4)
- [x] Verify `pixi run docs-build` (strict) and `pixi run ci` green

## Dev Notes

- Grounded in the real app: routes (`/upload`, `/history`, `/keys`, `/members`, `/results/:taskId`), the tab order (`Overview, SBOM, Vulnerabilities, Licenses, Dependency Graph, Version Currency`), the manifest `Format` choices (`requirements.txt`, `pyproject.toml`, `pixi.toml`, `pixi.lock`, `conda environment.yml`), the output formats (`CycloneDX JSON/XML`, `SPDX JSON`), the 10-key limit and `Authorization: Api-Key <key>` scheme.
- Screenshots deferred to Epic 12 (UI polish) per Story 11.7 — placeholders are admonition notes, no image files or broken links.
- Scope limited to `docs/user-guide/**` + the User Guide nav section so it merges cleanly alongside the other content stories.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Seven-page guide under `docs/user-guide/`, added to the nav as a section using the `navigation.indexes` pattern (index page as the section landing).
- `api-keys.md` cross-links to the API Reference section and mentions the `/api/docs/` Swagger UI (Story 11.9).

### File List

- `docs/user-guide/index.md`
- `docs/user-guide/accounts-and-organizations.md`
- `docs/user-guide/generating-an-sbom.md`
- `docs/user-guide/reading-the-results.md`
- `docs/user-guide/exporting-and-downloading.md`
- `docs/user-guide/job-history.md`
- `docs/user-guide/api-keys.md`
- `mkdocs.yml`
