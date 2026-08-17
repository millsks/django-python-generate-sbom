# Story 21.22: Distribution Identity Rename (L4)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 21.21**. Carries **rebrand layer L4** — the machine-readable identity, as
> distinct from 21.21's user-facing copy. Runs after 21.19 so it is not competing with file moves and
> deletions.

> **Scope boundary:** **Layer L5 — external identity (the GitHub repo name, the docs-site URL, the SonarCloud
> project key, the Codecov project) is explicitly OUT OF SCOPE**, by product-owner decision. A SonarCloud
> `projectKey` cannot be renamed without permanently losing all historical analysis, which is a large part of
> why it stays.

## Story

As a maintainer,
I want the project's packaging and configuration identity renamed,
so that the distribution, containers, and tooling refer to the product by its actual name.

## Acceptance Criteria

1. **The project and distribution names change.**
   Given `pixi.toml:8` declares `name = "django-python-generate-sbom"` and `pyproject.toml` declares the
   distribution `generate-sbom`, when the identity is renamed, then both carry the new name (for example
   `python-inventory-supply-lens`), `pixi run build` produces a correspondingly named wheel, and
   `pixi install` still resolves the editable install.
2. **The Python import name is unaffected.**
   Given the app is imported as `inventory` (Story 21.1 AC #2), when the distribution is renamed, then the
   **import** names `config`, `django_service`, and `inventory` are **unchanged** — the distribution name and
   the import name are deliberately different.
3. **Container, env, and tooling config follow.**
   Given `docker-compose.yml`, the four `.env*.example` files, `cliff.toml`, `.vscode/settings.json`, and
   `.github/workflows/release.yml` all carry the old identity, when they are renamed, then each uses the new
   name, the Compose stack still builds and starts, and the release workflow still produces a correctly named
   artifact.
4. **History is not rewritten.**
   Given `CHANGELOG.md` records released history under the old name, when the rename lands, then existing
   changelog entries and git tags are **left untouched** and only forward-looking configuration changes.
5. **The L5 exclusion is recorded in place.**
   Given external identity is deliberately unchanged, when the story completes, then
   `sonar-project.properties` `projectKey`/`projectName` (`:10`, `:17`), the GitHub repo URL, and the docs-site
   URL are confirmed **unchanged**, with the reason recorded **in the file** so a later contributor does not
   "fix" the inconsistency by accident.
6. **Gate green.**
   When the story completes, then `pixi run ci` exits 0, the Docker image builds, and a test asserts the
   distribution name matches the declared project name.

## Tasks / Subtasks

- [ ] **Task 1 — `pixi.toml` + `pyproject.toml` names (AC: #1, #2)** — Confirm the wheel builds and the
  editable install still resolves; confirm import names unchanged.
- [ ] **Task 2 — Compose + env examples (AC: #3)** — `docker-compose.yml`, `.env.example`,
  `.env.local.example`, `.env.container.example`, and the stray `.env.local copy.example`.
- [ ] **Task 3 — `cliff.toml`, `.vscode/settings.json`, `release.yml` (AC: #3)**.
- [ ] **Task 4 — Leave history alone (AC: #4)** — Explicitly verify no changelog/tag rewrite.
- [ ] **Task 5 — Record the L5 exclusion (AC: #5)** — Comment in `sonar-project.properties`.
- [ ] **Task 6 — Tests + gate (AC: #6)**.

## Dev Notes

### Grounded facts (verified)

- `pixi.toml:8` — `name = "django-python-generate-sbom"`; `:10` — `version = "0.1.0"`.
- `backend/pyproject.toml` — `name = "generate-sbom"`, `[tool.hatch.build.targets.wheel]`.
- `sonar-project.properties:10` — `sonar.projectKey=millsks_django-python-generate-sbom`; `:11` —
  `sonar.organization=millsks`; `:17` — `sonar.projectName=django-python-generate-sbom`.
- `mkdocs.yml:5-7` — `site_url`, `repo_url`, `repo_name` all reference
  `millsks/django-python-generate-sbom` (**L5 — unchanged**).
- Files carrying the old identity at root: `.env.example`, `.env.local.example`, `.env.container.example`,
  `.env.local copy.example`, `docker-compose.yml`, `cliff.toml`, `.vscode/settings.json`, `codecov.yml`,
  `mkdocs.yml`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `sonar-project.properties`,
  `pixi.lock`, `.github/workflows/release.yml`.
- `frontend/src/config.ts` also carried `REPO_URL`/`DOCS_URL`; those move to Django settings in Story 21.18 and
  keep their **L5** values.

### Distribution name ≠ import name — say so in the file

`python-inventory-supply-lens` (distribution) providing `inventory` (import) is normal Python packaging but
surprises people. Add a comment in `pyproject.toml` next to the name so the divergence reads as deliberate.

### Watch for

- **`.env.local copy.example`** is an untracked stray file at the repo root (it appeared in `git status` at the
  start of this work). Decide whether to rename or delete it — do not silently leave a half-renamed duplicate.
- **`pixi.lock`** embeds the project name. It regenerates; do not hand-edit it.
- **The editable install path** in `[pypi-dependencies]` was already repointed in Story 21.1 — renaming the
  distribution must not break it.

### Testing standards

- A test asserting `importlib.metadata.version(<new-dist-name>)` resolves, and that `inventory`,
  `django_service`, and `config` all import.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.22: Distribution Identity Rename (L4)]
- `pixi.toml`, `pyproject.toml`, `docker-compose.yml`, `.env*.example`, `cliff.toml`,
  `.vscode/settings.json`, `.github/workflows/release.yml`, `sonar-project.properties`.
- Upstream: `21-21-documentation-reconciliation-and-product-copy-rename.md`.

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
