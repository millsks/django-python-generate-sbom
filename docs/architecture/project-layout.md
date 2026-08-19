# Project Layout

The repository uses a **`src/` layout under a pixi umbrella** (AD-13), adopted from the
`django-15-factor-base` reference application. One `pixi.toml` at the root manages the
Python environment and every task — there is no second toolchain and no Node.

```text
django-python-generate-sbom/          # repo root == BASE_DIR (pixi umbrella)
  pixi.toml                           # the single environment + every task; no cwd
  pixi.lock
  pyproject.toml                      # Python tool config (pytest, ruff, mypy), package
                                      # metadata, and the ONLY import-root declaration
  manage.py
  mkdocs.yml                          # this documentation site
  docs/                               # documentation sources (Markdown)
  src/
    config/                           # Django project configuration
      settings/                       # base.py · local.py · test.py · production.py
      celery_app.py                   # Celery app + beat schedule
      urls.py                         # page routes, API routes, /api/schema, /api/docs
    django_service/                   # the HOST project
      users/                          # the concrete User model — owned here, not by the app
      templates/                      # base.html · landing.html · nav · 404/500
      static/                         # vendored Bootstrap · htmx · icons.svg
      icons.py                        # semantic icon map, used by the {% icon %} tag
      views.py                        # landing page · shell preview
    django_apps/                      # a PATH ROOT, not a package — carries no __init__.py
      inventory/                      # the single reusable app, imported as `inventory`
        common/                       # OrgScopedModel · access mixins · the user seam
        users/                        # Org · OrgMembership · OrgApiKey · auth
        manifests/                    # ManifestUpload · upload · format detection
        sbom/                         # SBOMJob · generation · pages.py · tables.py
          parsers/                    # requirements · pyproject · pixi · conda
        analysis/                     # AnalysisReport · reports.py · tables.py · excel.py
          services/                   # vulnerability · license · versions
        tasks/
          sbom_pipeline.py            # the 8-phase Celery chain (pipeline queue)
          analysis.py                 # the parallel analysis group (analysis queue)
          maintenance.py              # scheduled Beat jobs
        management/commands/          # must sit at the app root — Django looks nowhere else
        templates/inventory/          # app-owned; found via APP_DIRS, not the host project
        static/inventory/
        migrations/
  tests/                              # at the ROOT, not under src/
    unit/                             # mirrors the src/ tree; no I/O
    integration/                      # real DB; @pytest.mark.integration
  docker-compose.yml
```

## Conventions

- **One app, imported unqualified** — all domain code lives in `inventory`, and is
  imported as `from inventory.sbom import services`, never `django_apps.inventory`.
  `src/django_apps/` is a path root rather than a package (no `__init__.py`), which is
  what makes that work (AD-16).
- **`pyproject.toml` is the only place an import root is declared** — the
  `[tool.hatch.build.targets.wheel] sources` block. Nothing else may add one, or a
  source checkout and the built wheel will disagree about what `inventory` means.
- **Page views call services, never the HTTP API** — server-rendered views live in
  `pages.py` beside the DRF `views.py`; both call the same `services.py` / `selectors.py`
  functions, and neither calls the other over HTTP (AD-15).
- **Service functions carry the logic** — a package's `services.py` holds behavior; views
  and Celery tasks are thin callers (AD-3).
- **Tests mirror the source tree** — `tests/unit/test_<module>.py` shadows the module it
  covers. See [Testing](../developer/testing.md).
- **Python style**: PEP 8, 120-col, full type hints, Google-style docstrings; `ruff`
  formats/lints and `mypy` type-checks under strict settings.
