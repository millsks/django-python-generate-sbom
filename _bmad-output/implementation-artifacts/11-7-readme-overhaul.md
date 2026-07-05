# Story 11.7: README Overhaul

Status: review

## Story

As a visitor to the repository,
I want a README that explains the project at a glance,
so that I understand what it does and where to go next.

## Acceptance Criteria

1. README is a proper project front page: name + one-line description, a status-badge row, a short overview, a features summary, screenshots (placeholder), a Quick Start (`pixi install` → run the stack), and prominent links to the docs site and CONTRIBUTING (FR-DOC7).
2. Badge row (reference style: millsks/conventional-commit-hook), but app is unpublished — includes CI, Codecov, latest GitHub Release, static supported-Python-versions, and License; **explicitly no** PyPI-version or conda-forge-version badge.
3. Badge row also carries a tidy subset of beneficial extras (docs site, SonarCloud, pre-commit, Ruff, mypy, Conventional Commits) — no badge clutter.
4. README links to (rather than duplicates) the User Guide, Developer docs, and API reference, and includes the License section.

## Tasks / Subtasks

- [x] Rewrite `README.md` front page: title, description, overview, features (AC #1)
- [x] Author the two-row badge block — status + tooling — with GitHub Release replacing PyPI/conda version badges, static Python-versions badge, and a note explaining the omission (AC #2, #3)
- [x] Add a Documentation section linking the published site + User Guide / How-To / Developer / API Reference, and CONTRIBUTING (AC #1, #4)
- [x] Add a Screenshots section with a placeholder note (no broken image links / no image files) (AC #1)
- [x] Keep Quick Start (pixi + Docker stack) and the Development task table; add docs tasks (AC #1)
- [x] Verify `pixi run ci` green

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Badges (two rows): **status** — CI (`ci.yml`), Codecov, SonarCloud quality gate, latest GitHub Release (`img.shields.io/github/v/release/...`), static Python `3.12 | 3.13 | 3.14` (not `pypi/pyversions`, which needs publication), License (Apache 2.0); **tooling** — docs site (GitHub Pages), pre-commit, Ruff, typed/mypy, Conventional Commits. No PyPI-version or conda-forge-version badge, per the story; an explicit note states why.
- Docs links point at the Story 11.1 Pages site (`https://millsks.github.io/django-python-generate-sbom/`) and its sections; content is linked, not duplicated. The detailed register/upload walkthrough was trimmed to a short Quick Start that defers to the User Guide.
- Screenshots are a placeholder note only — real screenshots land with Epic 12 (no image files committed, no broken links).
- No code changed; `pixi run ci` re-verified green in this worktree.

### File List

- `README.md` (rewritten)
- `_bmad-output/implementation-artifacts/11-7-readme-overhaul.md` (new)
