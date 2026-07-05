# Story 11.1: Documentation Site Scaffold & GitHub Pages Deployment

Status: review

## Story

As a maintainer,
I want a MkDocs Material site wired into pixi and auto-deployed to GitHub Pages,
so that all subsequent documentation has a home that publishes automatically.

## Acceptance Criteria

1. `mkdocs-material` and `mkdocstrings-python` added as conda-forge dev deps; `mkdocs.yml` configures the Material theme (nav, search, light/dark palette toggle, repo link); `docs/index.md` landing page exists (FR-DOC1).
2. `pixi run docs-serve` (live reload) and `pixi run docs-build` (`mkdocs build --strict`) defined; `docs-build` runnable in CI.
3. `.github/workflows/docs.yml` builds and deploys to GitHub Pages via `configure-pages` + `upload-pages-artifact` + `deploy-pages` with `pages: write` / `id-token: write`.
4. Operator step documented (enable Pages, source = GitHub Actions); `mkdocs build --strict` wired so `pixi run ci` stays green.
5. Nav skeleton establishes the top-level sections (Home, User Guide, How-To, Developer, API Reference, Contributing) as placeholders for later stories.

## Tasks / Subtasks

- [x] Add `mkdocs-material` + `mkdocstrings-python` to `[feature.dev.dependencies]` (AC #1)
- [x] Author `mkdocs.yml` — Material theme, palette toggle, repo link, nav skeleton (AC #1, #5)
- [x] Create `docs/index.md` + section placeholder pages (all in nav, strict-clean) (AC #1, #5)
- [x] Add `docs-serve` / `docs-build` pixi tasks; wire `docs-build` into the `ci` umbrella (AC #2, #4)
- [x] Add `.github/workflows/docs.yml` Pages deploy workflow (AC #3)
- [x] Document the operator prerequisite (AC #4)
- [x] Verify `pixi run docs-build` and `pixi run ci` green

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Toolchain per Epic 11 decision: MkDocs Material + `mkdocstrings-python` (added as a dep for Story 11.4; the mkdocstrings plugin is intentionally **not** enabled yet — 11.4 wires the code reference to avoid Django-import issues under `--strict` now).
- `mkdocs.yml` uses Material's `red` primary + `amber` accent as a scaffold nod to the brand palette; the app's exact theme is Epic 12's concern (separate from the docs theme).
- `docs-build` runs `mkdocs build --strict` and is included in the `ci` depends-on, so the local gate fails on broken nav/links. The red "MkDocs 2.0" block printed during the build is Material's promotional banner, not a strict warning — the build exits 0.
- `docs.yml` deploys only when `docs/**`, `mkdocs.yml`, or the workflow change (plus `workflow_dispatch`).
- Site output dir `site/` was already covered by `.gitignore`.

### Operator Prerequisite

Enable GitHub Pages: repo **Settings → Pages → Build and deployment → Source = "GitHub Actions"**. GitHub Pages requires a public repository or a paid plan for private repos. Until enabled, the `deploy` job of `docs.yml` will fail (the `build` job still validates the site).

### File List

- `pixi.toml` (deps + `docs-serve`/`docs-build` tasks + `ci` depends-on)
- `pixi.lock`
- `mkdocs.yml` (new)
- `docs/index.md`, `docs/user-guide/index.md`, `docs/how-to/index.md`, `docs/developer/index.md`, `docs/api/index.md`, `docs/contributing.md` (new)
- `.github/workflows/docs.yml` (new)
