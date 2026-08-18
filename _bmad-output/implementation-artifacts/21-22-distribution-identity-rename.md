---
baseline_commit: cb1ff12
---

# Story 21.22: Distribution Identity Rename (L4)

Status: review

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

- [x] **Task 1 — `pixi.toml` + `pyproject.toml` names (AC: #1, #2)** — Confirm the wheel builds and the
  editable install still resolves; confirm import names unchanged.
- [x] **Task 2 — Compose + env examples (AC: #3)** — `docker-compose.yml`, `.env.example`,
  `.env.local.example`, `.env.container.example`, and the stray `.env.local copy.example`.
- [x] **Task 3 — `cliff.toml`, `.vscode/settings.json`, `release.yml` (AC: #3)**.
- [x] **Task 4 — Leave history alone (AC: #4)** — Explicitly verify no changelog/tag rewrite.
- [x] **Task 5 — Record the L5 exclusion (AC: #5)** — Comment in `sonar-project.properties`.
- [x] **Task 6 — Tests + gate (AC: #6)**.

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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. **879 passed** (up from 863), coverage **96.72%**.
- **16 new tests** in `tests/unit/test_distribution_identity.py`.
- New distribution name: **`python-inventory-supply-lens`**. `pixi run build` produces
  `python_inventory_supply_lens-0.1.0-py3-none-any.whl`; `pixi install` re-solved and
  `pixi.lock` now contains **zero** occurrences of the old name.
- **Docker image built and run** (AC #6): `docker build` succeeds — `pixi install --locked`
  then `collectstatic` (191 files, 344 post-processed). Inside the image,
  `version("python-inventory-supply-lens")` → `0.1.0` and `inventory`, `config`, and
  `django_service` all import unqualified.
- `.env.example`, `.env.local.example`, `.env.container.example` carry **no** identity
  string — their `sbom` occurrences are the Postgres database/user and the S3 bucket name
  (`sbom-artifacts`), which are domain values, not the product name. Left unchanged.
- The stray `.env.local copy.example` named in the Dev Notes was already deleted earlier in
  this epic with product-owner approval; nothing half-renamed remains.

### Completion Notes List

**Three names now do three jobs, and the divergence is written down where each is
declared.** The **product** is "Python Inventory Supply Lens" (Story 21.21), the
**distribution** is `python-inventory-supply-lens` (this story), and the **imports** stay
`config`, `django_service`, and `inventory`. Installing the distribution gives you
`import inventory` — ordinary Python packaging that reliably surprises people — so
`pyproject.toml` says so in a comment beside the name, as the Dev Notes asked.

**Renaming the distribution silently breaks the footer version, and a test now catches
that.** `PRODUCT_VERSION` resolves `importlib.metadata.version("generate-sbom")` by
literal string (added in Story 21.18). Renaming the distribution without updating that
lookup does not raise — the `PackageNotFoundError` branch falls back to `"0.0.0"`, and the
footer shows a wrong version forever. Updated, and
`test_the_footer_version_still_resolves` asserts it equals the installed version rather
than merely being non-empty.

**AC #3 lists `.vscode/settings.json` among the files to rename. It must not be.** Its only
occurrence is the SonarCloud `projectKey`, which is layer **L5** — the same value
`sonar-project.properties` carries, and the one the story's own scope boundary says is out
of scope. Renaming it there would silently disconnect SonarLint from the project while
leaving the server-side config correct. I left it, and recorded the reason where a reader
will look, with a test asserting the two stay bound to the same key.

**The L5 exclusion note explains the cost, not just the rule.** A comment saying "do not
rename" invites someone to rename it anyway. The note in `sonar-project.properties` says a
`projectKey` cannot be renamed and that creating a new project discards every historical
analysis, the new-code baseline, and the issue triage — and each L5 test states its own
reason, so a failure explains itself rather than reading as an arbitrary constraint.

### Two defects found while in here, both fixed

**1. Story 21.19 missed `.github/workflows/release.yml`, and the next release would have
failed.** It still ran `pixi run fe-build` and tarred `frontend/dist` — a task and a
directory that no longer exist. 21.19's AC #4 named `ci.yml` and `maintenance.yml` only, and
my removal test in that story checked exactly those files, so nothing caught it. AC #3 names
`release.yml` here, so it is fixed in scope: the frontend bundle step, its release-notes row,
and its upload entry are gone, and the wheel row now names the new artifact. The guard test
strips comment lines before asserting, because the file legitimately *explains* that the step
was removed and a test forbidding that would push the history out of the place it is most
useful.

**2. Story 21.21 left one stale dotted import path.** `docs/deployment/openshift/reference.md`
still named `generate_sbom.common.storage.PublicEndpointS3Storage`; the real path has been
`inventory.common.storage.PublicEndpointS3Storage` since Story 21.2. That sweep searched for
`backend/`-prefixed *file* paths, not dotted *module* paths, which is why it survived. Fixed
and verified against `production.py`.

**History is untouched (AC #4).** `CHANGELOG.md` still records what shipped under the old
name, and no git tag was moved. There is a test asserting the changelog still contains the
old identity — the inverse of the usual assertion, because *removing* it would be the defect.

**`pixi.lock` was re-solved, not hand-edited**, as the Dev Notes required. It now contains
zero occurrences of the old distribution name, and the editable install still resolves — the
`[pypi-dependencies]` key had to be renamed in lockstep with `[project] name`, and a mismatch
there installs nothing and fails later at import time, far from the cause. A test pins both.

**Not renamed, deliberately:** the GitHub repository, the docs-site URL, the SonarCloud
project key and name, and the `.pptx`/`.pdf` deck filenames. The README's opening note and
`mkdocs.yml`'s comment already explain the first two to a reader who notices the mismatch.

**Still open, unchanged:** Story 21.24 (remove the authentication requirement) is the last
outstanding story of the epic, and Story 21.23's AC #4 product-owner walkthrough remains —
along with the brand-palette finding from that audit and Story 21.18's side-by-side visual
review. The `beat_schedule` maintenance tasks are still absent from the Celery registry;
`solution-design.md` and `architecture-diagrams.html` still carry Story 21.20's
not-reconciled notices; AD-9 still needs an Epic 20 correct-course; the decks still need
re-rendering.

### File List

**New (1)**
- `tests/unit/test_distribution_identity.py` (16 tests) — the distribution name, the
  unchanged import names, and each L5 exclusion with its reason

**Modified (8)**
- `pyproject.toml` — distribution renamed, with the distribution-vs-import note
- `pixi.toml` / `pixi.lock` — `[workspace] name` and the editable-install key; lock re-solved
- `src/config/settings/base.py` — the `PRODUCT_VERSION` distribution lookup
- `.github/workflows/release.yml` — frontend bundle step removed (Story 21.19 leftover);
  wheel artifact renamed
- `sonar-project.properties` — the L5 exclusion recorded in place, covering
  `.vscode/settings.json` too
- `docker-compose.yml`, `cliff.toml` — header comments
- `docs/deployment/openshift/reference.md` — stale `generate_sbom.` module path
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

**Deliberately unchanged:** `.vscode/settings.json` (SonarLint binding — L5),
`sonar.projectKey`/`projectName`, `mkdocs.yml`'s `site_url`/`repo_url`/`repo_name`,
`CHANGELOG.md`, git tags, and the `.env*.example` files.

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Renamed the distribution to `python-inventory-supply-lens` across `pyproject.toml`, `pixi.toml`, the re-solved lock, the `PRODUCT_VERSION` lookup, and the release workflow's artifact name, while leaving the import names `config` / `django_service` / `inventory` untouched — the divergence is now documented beside the declaration. Verified end to end: the wheel builds under the new name, and the Docker image builds and resolves the distribution while still importing `inventory` unqualified. Recorded the L5 exclusion in `sonar-project.properties` with the cost spelled out, and did **not** rename `.vscode/settings.json` despite AC #3 listing it — its only occurrence is the SonarLint binding to that same immutable project key. Found and fixed two defects from earlier stories: `release.yml` still ran the deleted `pixi run fe-build` and would have failed the next release, and one stale `generate_sbom.` module path survived Story 21.21's sweep because that sweep searched file paths rather than dotted paths. `pixi run ci` exit 0; 879 tests at 96.72%. |
