# Product-Rename Residue Audit

Story 21.21 renamed the **product** to **Python Inventory Supply Lens** ("Supply Lens"
for short). It did **not** rename the artifact the product makes: "SBOM", "CycloneDX",
and "SPDX" stay wherever they name the document or the standard.

That distinction means a find-and-replace would have been wrong, so this page accounts
for every remaining occurrence instead. It is the acceptance evidence for Story 21.21
AC #5 and is expected to shrink when Story 21.22 renames the distribution identity.

## Method

Case-insensitive search for `sbom` across the repository, excluding `.git/`, `.pixi/`,
`site/`, `staticfiles/`, `media/`, tool caches, and the `_bmad*` planning trees. Of
those files, the ones containing a **product-name-shaped** occurrence — `generate-sbom`,
`generate sbom`, or `Generate SBOM` — are then classified.

Anything matching only the bare word "SBOM" is the domain term and is **not** listed:
that is the artifact, and it is correct everywhere it appears.

## Totals

| Measure | Count |
|---|---|
| Files containing case-insensitive `sbom` | 132 |
| …of those, files with a product-name-shaped occurrence | 30 |
| Total product-name-shaped occurrences | 67 |
| Occurrences **renamed** by this story | 0 remaining (all prose uses converted) |
| Occurrences **retained**, classified below | 67 |

## Classification

Every one of the 67 falls into one of five buckets. None is unreviewed.

### 1 · External identity — layer L5, deliberately never renamed (28)

The GitHub repository, the published docs-site URL, the SonarCloud project key, and the
Codecov project keep the original identifier. Renaming them breaks every published link,
and a SonarCloud `projectKey` cannot be changed without permanently discarding the
project's analysis history. This exclusion is a product-owner decision recorded in
Story 21.22.

| File | Count | What it is |
|---|---|---|
| `README.md` | 19 | Badge image/target URLs and docs-site links |
| `CONTRIBUTING.md` | 5 | Links to `CODE_OF_CONDUCT.md`, `SECURITY.md`, `LICENSE`, the clone URL |
| `sonar-project.properties` | 3 | `projectKey`, `projectName`, `organization` |
| `SECURITY.md` | 1 | The private-vulnerability-reporting URL |

### 2 · Distribution identity — layer L4, renamed by Story 21.22 (13)

Machine-readable packaging and tooling identity. Out of scope here by design: 21.21 is
user-facing copy, 21.22 is the distribution.

| File | Count | What it is |
|---|---|---|
| `src/config/settings/base.py` | 5 | Distribution name in `importlib.metadata.version()` and env-prefix docstrings |
| `pixi.toml` | 2 | `[workspace] name` |
| `cliff.toml` | 2 | Changelog generation config |
| `pyproject.toml` | 1 | Distribution name |
| `pixi.lock` | 1 | Resolved editable install |
| `docker-compose.yml` | 1 | Project/image name |
| `.vscode/settings.json` | 1 | Workspace config |

### 3 · Released history — never rewritten (2)

| File | Count | Why |
|---|---|---|
| `CHANGELOG.md` | 2 | Entries record what shipped under the old name. Story 21.22 AC #4 forbids rewriting history or tags. |

### 4 · Domain vocabulary and UI labels — correct as they stand (13)

These are not the product name. They are the action the user takes, the phase the
pipeline runs, or a file path.

| File | Count | What it is |
|---|---|---|
| `src/django_apps/inventory/templates/inventory/sbom/upload.html` | 1 | The **"Generate SBOM"** submit button — the action, not the product |
| `src/django_apps/inventory/tasks/sbom_pipeline.py` | 1 | The progress string `"generate SBOM document"` — phase 3's name |
| `src/config/{asgi,wsgi,celery_app}.py` | 3 | Module docstrings naming the project directory |
| `src/django_apps/inventory/__init__.py` | 1 | Docstring naming the project |
| `docs/user-guide/generating-an-sbom.md` | 1 | Instructs the reader to choose the **Generate SBOM** button |
| `docs/user-guide/{api-keys,accounts-and-organizations}.md` | 2 | "generate SBOMs" as a verb phrase |
| `docs/developer/pipeline.md` | 1 | Phase 3, **"Generate SBOM document"** |
| `docs/developer/project-layout.md` | 1 | The repo root **directory** name in the source tree |
| `docs/how-to/{index,interpret-vulnerabilities}.md` | 2 | Links to `generate-sbom.md` — a filename |

### 5 · Tests asserting the above (4)

| File | Count | What it asserts |
|---|---|---|
| `tests/unit/test_landing_page.py` | 2 | The distribution name resolves, and the repo URL is the L5 default |
| `tests/unit/test_ui_shell.py` | 1 | The old product name **must not** appear in the shell |
| `tests/unit/test_api_schema.py` | 1 | The OpenAPI schema's distribution metadata |

## Known stale artifacts

`presentations/Generate-SBOM-Executive-Overview.{pptx,pdf}` were rendered before the
rename and still show the old name and a React UI. The Markdown source beside them is
updated and is the source of truth; the binaries need re-rendering, which is not
something this story could do. The **filenames** are left alone deliberately — renaming
them is distribution identity, not product copy.
