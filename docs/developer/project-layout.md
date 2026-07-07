# Project Layout

The repository is a **monorepo under a pixi umbrella** (AD-13): `backend/` and
`frontend/` are project-root peers, and one `pixi.toml` at the root manages the Python
environment, the Node runtime, and every task.

```text
django-python-generate-sbom/          # project root (pixi umbrella environment)
  pixi.toml                           # umbrella: Python env + Node runtime + all tasks
  pixi.lock                           # pins Python AND Node deps
  mkdocs.yml                          # this documentation site
  docs/                               # documentation sources (Markdown)
  backend/                            # Django + Celery
    config/
      settings/                       # base.py · local.py · production.py
      celery_app.py                   # Celery app + beat schedule
      urls.py                         # API routes (incl. /api/schema, /api/docs)
    generate_sbom/                    # the Django project package
      common/                         # OrgScopedModel + shared abstractions
      users/                          # User · Org · OrgMembership · OrgApiKey
      manifests/                      # ManifestUpload · upload · format detection
      sbom/                           # SBOMJob · generation
        parsers/                      # requirements · pyproject · pixi · conda
      analysis/                       # AnalysisReport
        services/                     # vulnerability · license · versions
      tasks/
        sbom_pipeline.py              # the 8-phase Celery chain (pipeline queue)
        analysis.py                   # the parallel analysis group (analysis queue)
        maintenance.py                # scheduled Beat jobs
    tests/
      unit/                           # mirrors generate_sbom/; no I/O
      integration/                    # real DB; @pytest.mark.integration
    manage.py
    pyproject.toml                    # Python tool config (pytest, ruff, mypy) + metadata
  frontend/                           # React SPA (Vite + MUI) — peer to backend/
    src/
      api/                            # REST client — all fetch calls live here
      components/                     # shared UI components
      pages/                          # route-level page components
    package.json                      # npm manages JS deps; pixi provides Node + tasks
    vite.config.ts
  docker-compose.yml
```

## Conventions

- **`api/` is the single boundary to the backend** on the frontend — all `fetch`
  calls live under `frontend/src/api/`, never inline in components (AD-5).
- **Service functions carry the logic** — a Django app's `services.py` holds
  behavior; views and Celery tasks are thin callers (AD-3).
- **Tests mirror the source tree** — `tests/unit/test_<module>.py` shadows
  `generate_sbom/<module>.py`. See [Testing](testing.md).
- **Python style**: PEP 8, 120-col, full type hints, Google-style docstrings; `ruff`
  formats/lints and `mypy` type-checks under strict settings.
