# Story 1.1: Backend Scaffold & Developer Toolchain

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a configured backend project scaffold with consistent tooling,
so that I can start implementing features immediately without setup decisions.

## Acceptance Criteria

1. Given a fresh clone of the repository, when I `cd backend/` and run `pixi install`, then all dependencies install without error and the pixi environment is ready.
2. Given the `backend/` directory with the initial scaffold, when I run `pixi run fmt && pixi run lint && pixi run check`, then all three pass on the initial scaffold with zero errors or warnings.
3. Given the `backend/` directory, when I run `pixi run test`, then the pytest test suite runs and exits 0 (zero tests collected is acceptable at this stage).
4. Given the `backend/` directory, when I run `pixi run ci`, then all five steps pass: pre-commit, build, mypy (strict), ruff, cov.
5. Given a git commit with a non-Conventional-Commits message (e.g., "updated stuff"), when the commit-msg pre-commit hook runs, then the hook rejects the commit with an informative error.
6. Given the project root, when I inspect the directory layout, then `manage.py`, `pixi.toml`, and `pyproject.toml` live under `backend/`; `docker-compose.yml`, `README.md`, and `LICENSE` (Apache 2.0) live at the project root; `frontend/` is a peer to `backend/` (AD-13).
7. Given `pyproject.toml` in `backend/`, when ruff and mypy configurations are read, then ruff `line-length=120`, mypy `strict=true`, Google-style docstrings enforced, Python 3.10+ union syntax required.
8. Given `.github/workflows/ci.yml`, when a push or PR is opened against `main`, then the `unit` job runs `pixi run test` and the `full` job runs `pixi run ci` across the Python matrix (3.12, 3.13, 3.14-dev).

## Tasks / Subtasks

- [ ] Task 1 — Establish the AD-13 monorepo skeleton (AC: #6)
  - [ ] Create project-root `backend/` and `frontend/` directories as peers
  - [ ] Place `docker-compose.yml` (may be a stub committed in Story 1.2), `README.md`, and `LICENSE` (Apache 2.0 full text) at the project root
  - [ ] Confirm `.gitignore` already ignores `.pixi/`, `.env`, `__pycache__/`, tool caches, `.DS_Store` (already present in repo root)
- [ ] Task 2 — Generate the Django scaffold under `backend/` (AC: #1, #6)
  - [ ] Generate the Django project structure using cookiecutter-django 2026.26.4 with Celery + Redis + PostgreSQL + S3 options (see Dev Notes → Scaffold reconciliation before running)
  - [ ] Relocate/normalize the generated tree to the `backend/` layout: `config/settings/{base,local,production}.py`, `config/celery_app.py`, `config/urls.py`, `config/wsgi.py`, `manage.py`, and the `<project_slug>/` package holding app modules
  - [ ] Remove generated tooling that conflicts with the pixi standard (pip/uv requirements files, tox, generated GitHub Actions) — pixi is the single source of truth
- [ ] Task 3 — Author `backend/pixi.toml` via `pixi init` then edit (AC: #1, #2, #3, #4)
  - [ ] Run `pixi init backend` (or `pixi init` inside `backend/`) so the file uses the current `[workspace]` table — never hand-write `pixi.toml`
  - [ ] Add runtime deps (conda-forge first): django, djangorestframework, celery, redis-py, structlog, psycopg, gunicorn, whitenoise, django-environ; add pypi-only deps under `[pypi-dependencies]` (djangorestframework-api-key, django-storages, cyclonedx-python-lib, lib4sbom, etc. — only those needed later; Story 1.1 only needs the web/runtime core)
  - [ ] Add `[feature.dev.dependencies]`: pytest, pytest-cov, pytest-django, mypy, ruff, pre-commit, django-stubs, djangorestframework-stubs
  - [ ] Define the standard tasks: `bootstrap`, `fmt`, `lint`, `check`, `test`, `test-integration`, `cov`, `build`, `changelog`, `ci`, `act` (see Dev Notes → Pixi task definitions)
  - [ ] `ci` chains via `depends-on`: pre-commit → build → check → lint → cov
- [ ] Task 4 — Author `backend/pyproject.toml` (tool config only, no runtime deps) (AC: #7)
  - [ ] `[tool.pytest.ini_options]`: `testpaths=["tests"]`, `addopts="-v --tb=short"`, `DJANGO_SETTINGS_MODULE=config.settings.local`, `integration` marker registered
  - [ ] `[tool.ruff]` `line-length=120`, `src=["<project_slug>","tests"]`; `[tool.ruff.lint]` select `["E","F","I","UP","B","RUF","D"]`, ignore `["E501"]`; pydocstyle convention `google`
  - [ ] `[tool.mypy]` `python_version="3.12"`, `strict=true`, django-stubs + djangorestframework-stubs plugins configured
  - [ ] `[tool.git-cliff]` changelog + conventional commit parsers
- [ ] Task 5 — Configure pre-commit (AC: #4, #5)
  - [ ] `.pre-commit-config.yaml` at `backend/` (or repo root scoped to backend): conventional-pre-commit (commit-msg stage), ruff (`--fix`), ruff-format, mirrors-mypy
  - [ ] `pixi run bootstrap` installs the hooks (`pre-commit install --install-hooks --hook-type commit-msg --hook-type pre-commit`)
- [ ] Task 6 — Configure `.pixi/config.toml` (AC: #1)
  - [ ] `tls-root-certs = "system"`
- [ ] Task 7 — GitHub Actions CI (AC: #8)
  - [ ] `.github/workflows/ci.yml` with `unit` job (matrix 3.12/3.13/3.14-dev, runs `pixi run test`) and `full` job (matrix, runs `pixi run ci`); `continue-on-error` on 3.14-dev
  - [ ] setup-pixi action pinned; working directory set to `backend/`
- [ ] Task 8 — Verify the gate end-to-end (AC: #2, #3, #4)
  - [ ] Add one trivial passing unit test under `tests/unit/` so `pytest` and coverage exercise the harness
  - [ ] Run `pixi run ci` from `backend/` and confirm exit 0

## Dev Notes

### Scaffold reconciliation — READ FIRST (non-obvious)

The architecture (PRD addendum) selects **cookiecutter-django 2026.26.4** as the scaffold, but the project's global engineering standard mandates a **pixi** toolchain with a fixed set of `pixi run` tasks, ruff/mypy/pytest config in `pyproject.toml`, and the AD-13 `backend/` + `frontend/` monorepo layout. cookiecutter-django ships a pip/uv-based toolchain and its own layout, so the two do not drop in cleanly.

Reconciliation approach for this story:
- Use cookiecutter-django to generate the **Django application skeleton** (settings split, Celery wiring, users app, Docker assumptions) — this is what the addendum is buying.
- Immediately **re-home it into `backend/`** and **replace its toolchain with pixi** (this story's tasks 3–7). Discard generated `requirements/*.txt`, `setup.cfg`/`tox.ini`, and any generated CI in favor of `pixi.toml` + `pyproject.toml` + the standard `ci.yml`.
- The generated project package becomes the `<project_slug>/` package under `backend/`.

This tension is being surfaced to the user before build — do not proceed past Task 2 until the chosen scaffold path is confirmed (see the open question raised with this story).

### Stack versions (pinned by ARCHITECTURE-SPINE.md § Stack)

Target runtime: Python 3.14.6, Django 6.0.6, djangorestframework 3.17.1, Celery 5.6.3, structlog 26.1.0, WhiteNoise 6.12.0, gunicorn (per Docker), PostgreSQL 18.4, Redis 8.8.0. The CI **matrix** is 3.12 / 3.13 / 3.14-dev per AC #8 and the global standard; the pinned 3.14.6 is the deployment target. mypy `python_version` is set to `3.12` (floor of the matrix).

### Pixi task definitions (global standard § 4)

| Task | Command |
|---|---|
| `bootstrap` | `pre-commit install --install-hooks --hook-type commit-msg --hook-type pre-commit` |
| `fmt` | `ruff format .` |
| `lint` | `ruff check .` |
| `check` | `mypy <project_slug>/` |
| `test` | `pytest tests/unit/` |
| `test-integration` | `pytest tests/integration/` |
| `cov` | `pytest tests/ --cov=<project_slug> --cov-report=term-missing --cov-fail-under=90` |
| `build` | build the package distribution |
| `changelog` | `git cliff -o CHANGELOG.md` |
| `ci` | depends-on: pre-commit → build → check → lint → cov |
| `act` | `act --container-architecture linux/amd64` |

Note: coverage target path is the Django project package (`<project_slug>/`), not `src/` — cookiecutter-django does not use a src-layout. This is a deliberate divergence from the global src-layout default, driven by the cookiecutter-django scaffold choice (AD-13 fixes the app package under `backend/<project_slug>/`).

### Source tree this story establishes (ARCHITECTURE-SPINE.md § Source tree)

```
django-python-generate-sbom/          ← project root
  backend/                            ← THIS STORY
    config/
      settings/                       # base.py · local.py · production.py
      celery_app.py
      urls.py
      wsgi.py
    <project_slug>/                   # app modules added by later stories
    tests/
      unit/                           # mirrors app structure; no I/O
      integration/                    # real DB · broker='memory://' · @pytest.mark.integration
    manage.py
    pixi.toml
    pyproject.toml
    .env.example                      # created in Story 1.2
  frontend/                           # Story 1.4
  docker-compose.yml                  # Story 1.2
  README.md
  LICENSE                             # Apache 2.0 (NFR-5.4)
```

### Testing standards

- pytest + pytest-django; unit tests in `tests/unit/`, integration in `tests/integration/` marked `@pytest.mark.integration`.
- Coverage gate `--cov-fail-under=90` enforced in `cov`. For this scaffolding story, a single trivial unit test is enough to prove the harness; real coverage arrives with feature stories.
- Never `print()`; never stdlib `logging` — structlog only (configured fully in Story 1.3, but the dependency lands here).

### Constraints / guardrails

- Never write `pixi.toml` by hand — always `pixi init` first (global standard § 10), then edit.
- Never use `--no-verify`; never commit `.env` or secrets.
- Branch discipline: this work belongs on a `feature/` branch, not `main`.
- The Stop hook running `pixi run ci` must be present in `.claude/settings.json` before the first commit — add it if absent.

### Project Structure Notes

- AD-13 is the binding layout invariant: all `pixi run` commands execute from `backend/`. Do not place `pixi.toml`/`pyproject.toml` at the project root.
- No app modules (`users/`, `manifests/`, etc.) are created in this story — they arrive in their owning epics. This story only stands up `config/` + empty `<project_slug>/` package + tooling.
- No database models and therefore no migrations in this story (AC has no model work). `OrgScopedModel` is Story 1.3.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1: Backend Scaffold & Developer Toolchain]
- [Source: ARCHITECTURE-SPINE.md#AD-13 — Monorepo layout]
- [Source: ARCHITECTURE-SPINE.md#Stack]
- [Source: ARCHITECTURE-SPINE.md#Source tree]
- [Source: solution-design.md#2. Repository Layout]
- [Source: prd.md#NFR-5.1, NFR-5.2, NFR-5.3, NFR-5.4]
- [Source: PRD addendum.md#Technology Selections — cookiecutter-django 2026.26.4]
- [Source: global CLAUDE.md §4 Pixi Task Standard, §10 Project Scaffold]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
