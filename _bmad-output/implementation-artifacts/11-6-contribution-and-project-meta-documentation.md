# Story 11.6: Contribution & Project Meta-Documentation

Status: review

## Story

As a maintainer,
I want standard contribution and community health files,
So that contributors know how to work with the project and report issues securely.

See the full acceptance criteria under **Epic 11 → Story 11.6** in
`_bmad-output/planning-artifacts/epics.md`.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Completion Notes List

- Added `CONTRIBUTING.md` grounded in this repo's real conventions: Pixi setup
  (`pixi install` + `pixi run bootstrap`), the `feature/`/`bugfix/`/`hotfix/` branch
  naming, the pixi task reference, the authoritative `pixi run ci` gate (documenting its
  actual ordered steps), the tests-required policy (≥90% backend coverage), Conventional
  Commits via the commit-msg hook, and the PR process (auto-labeling, single concern).
- Added `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1, contact millsks@gmail.com).
- Added `SECURITY.md` — private vulnerability reporting via GitHub Security Advisories
  (with an email fallback); no public issues.
- Added `.github/ISSUE_TEMPLATE/bug_report.md` (labels: `bug`) and `feature_request.md`
  (labels: `enhancement`) aligned with the Story 9.6 label automation, plus
  `.github/PULL_REQUEST_TEMPLATE.md` (Conventional Commits + `pixi run ci` checklist).
- Surfaced CONTRIBUTING on the docs site without duplication: enabled
  `pymdownx.snippets` in `mkdocs.yml` and replaced the `docs/contributing.md` placeholder
  with a single-source include (`--8<-- "CONTRIBUTING.md"`); the existing **Contributing**
  nav entry resolves to it. Cross-references in CONTRIBUTING use absolute GitHub URLs so
  `mkdocs build --strict` stays clean.
- Verified: `pixi run docs-build` (strict) and `pixi run ci` both pass.

### File List

- `CONTRIBUTING.md` (new)
- `CODE_OF_CONDUCT.md` (new)
- `SECURITY.md` (new)
- `.github/ISSUE_TEMPLATE/bug_report.md` (new)
- `.github/ISSUE_TEMPLATE/feature_request.md` (new)
- `.github/PULL_REQUEST_TEMPLATE.md` (new)
- `docs/contributing.md` (replaced placeholder with snippet include)
- `mkdocs.yml` (added `pymdownx.snippets`)
