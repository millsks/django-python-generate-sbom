# Story 21.1: Restructure the Repository to a `src/` Layout

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** **FIRST story of Epic 21.** Everything else builds on the new layout — moving files *after* the
> Django templates exist would mean moving them twice. Deliberately **mechanical**: no app labels change, no
> models move, no migrations are touched, and the React SPA keeps working end to end. Story 21.2 does the
> risky part (label collapse + migration rewrite).

## Story

As a developer,
I want the Django project restructured into `src/config`, `src/django_service`, and `src/django_apps` with
`tests/` at the repository root,
so that the layout matches the `django-15-factor-base` reference application and the reusable app has a
natural, graduation-ready home.

## Acceptance Criteria

1. **The tree matches the reference layout.**
   Given `manage.py`, `pyproject.toml`, `config/`, `generate_sbom/`, and `tests/` all live under `backend/`,
   when the tree is restructured, then `src/config/` holds the settings/urls/wsgi/asgi/celery_app package,
   `src/django_service/` exists as the host-project package, `src/django_apps/` exists as a path root,
   `generate_sbom/` is relocated to `src/django_apps/inventory/` as a **straight move**, and `tests/`,
   `manage.py`, and `pyproject.toml` sit at the repository root. The four app labels are collapsed in Story
   21.2 and must **not** be pulled forward here.
2. **`src/django_apps/` is a path root, not a package, and the app imports unqualified.**
   Given the reference application's AD-6, when the layout lands, then `src/django_apps/` contains **no**
   `__init__.py`, `[tool.hatch.build.targets.wheel]` declares `only-include = ["src"]` and
   `sources = ["src", "src/django_apps"]`, and the app is importable and installable as **`inventory`** —
   unqualified — rather than `django_apps.inventory`.
3. **The hatchling prefix-shadowing trap is verified, not assumed.**
   Given hatchling normalises `sources` into a mapping, sorts it **ascending**, and applies the **first
   matching prefix** — so `"src"` sorts before and shadows `"src/django_apps"` — when the wheel is built, then
   a test **inspects the built wheel's top-level entries** and asserts `config`, `django_service`, and
   `inventory` are all present at the wheel root, failing if the app landed as `django_apps/inventory`.
4. **`BASE_DIR` and `APPS_DIR` resolve correctly.**
   Given `backend/config/settings/base.py:15` computes `BASE_DIR` with three `parent` hops (today =
   `backend/`), when the settings move to `src/config/settings/`, then `BASE_DIR` uses **four** hops to reach
   the repository root, `APPS_DIR = BASE_DIR / "src" / "django_service"` is introduced, and `STATIC_ROOT`
   (`:129`), `MEDIA_ROOT`, the default SQLite path (`:113`), and the celerybeat schedule path all resolve to
   their intended locations — verified by an explicit test, not by inspection.
5. **`pyproject.toml` is repointed at the new layout.**
   Given `backend/pyproject.toml` sets `packages = ["generate_sbom"]` (L15), `pythonpath = ["."]` (L23), ruff
   `src` (L31) and `known-first-party` (L50), django-stubs `django_settings_module` (L60), and coverage
   `source = ["generate_sbom"]` (L73), when the move lands, then every one of those resolves against `src/`,
   `known-first-party` becomes `["config", "django_service", "inventory", "tests"]`, and coverage measures
   `src/**`.
6. **Every pixi task works without `cwd = "backend"`.**
   Given **24** tasks in `pixi.toml` carry `cwd = "backend"`, when the move lands, then each drops it (or
   targets the new root), and `pixi run test`, `check`, `lint`, `cov`, `build`, `migrate`, `runserver`,
   `worker`, `beat`, `collectstatic`, and `dev` all still work.
7. **Build, CI, and quality tooling follow the move.**
   Given `Dockerfile` does `COPY backend/ backend/` before `pixi install --locked` — and the backend is an
   **editable** install whose source must be present at install time — when the move lands, then `Dockerfile`,
   `.github/workflows/ci.yml`, `sonar-project.properties` (`sonar.sources` L21, `sonar.tests` L22, coverage
   report path L28, `sonar.coverage.exclusions` L30, `sonar.test.inclusions` L33), and `codecov.yml` all
   reference the new paths and the editable-install ordering still holds.
8. **The React SPA is unaffected.**
   Given this story does not touch the frontend, when it lands, then `FRONTEND_DIST` / `STATICFILES_DIRS` /
   `SPA_INDEX_FILE` (`base.py:145-147`) still resolve to `frontend/dist/`, `pixi run fe-build` still works,
   WhiteNoise still serves the SPA, and every SPA route still loads.
9. **Gate green with no behavioural test changes.**
   Given the move is mechanical, when `pixi run ci` runs, then it exits 0 with coverage ≥90% and **no** test
   assertion changed except for import paths — any behavioural change is a signal the story overreached.

## Tasks / Subtasks

- [ ] **Task 1 — Move the tree (AC: #1)** — `git mv` `backend/config` → `src/config`,
  `backend/generate_sbom` → `src/django_apps/inventory`, `backend/tests` → `tests`, and
  `backend/{manage.py,pyproject.toml}` → repo root. Create `src/django_service/` (package, with
  `__init__.py`). Use `git mv` so history is preserved and the diff reads as renames.
- [ ] **Task 2 — Make `src/django_apps/` a path root (AC: #2)** — Ensure it has **no** `__init__.py`. Set
  `only-include = ["src"]` and `sources = ["src", "src/django_apps"]`.
- [ ] **Task 3 — Wheel verification test (AC: #3)** — Build the wheel and assert its top-level entries. This
  is the AC most likely to fail first; treat a `django_apps/inventory` result as the expected failure mode and
  resolve it in `sources`, not with a `sys.path` insert.
- [ ] **Task 4 — `BASE_DIR` / `APPS_DIR` (AC: #4)** — Correct the `parent` chain, introduce `APPS_DIR`, and add
  a unit test asserting the derived paths.
- [ ] **Task 5 — Repoint packaging + tool config (AC: #5)** — The six settings in `pyproject.toml`.
- [ ] **Task 6 — Strip `cwd` from pixi tasks (AC: #6)** — All 24 occurrences. Smoke-run each task group.
- [ ] **Task 7 — Dockerfile + CI + Sonar + Codecov (AC: #7)** — Update every `backend/` path reference.
- [ ] **Task 8 — Verify the SPA still works (AC: #8)** — `pixi run fe-build`, `collectstatic`, then load each
  SPA route against `pixi run runserver`.
- [ ] **Task 9 — Gate (AC: #9)** — `pixi run ci` to green; confirm the diff contains no assertion changes.

## Dev Notes

### Grounded facts (verified)

- `backend/pyproject.toml`: `packages = ["generate_sbom"]` L15, pytest `DJANGO_SETTINGS_MODULE` L21,
  `pythonpath = ["."]` L23, ruff `src` L31, `known-first-party` L50, django-stubs
  `django_settings_module = "config.settings.local"` L60, coverage `source` L73.
- `backend/config/settings/base.py`: `BASE_DIR` L15 (three `parent` hops), `INSTALLED_APPS` L23,
  `AUTH_USER_MODEL` L44, `STATIC_URL` L128, `STATIC_ROOT` L129, `FRONTEND_DIST` L145, `STATICFILES_DIRS` L146,
  `SPA_INDEX_FILE` L147.
- `pixi.toml`: **24** tasks carry `cwd = "backend"`.
- `sonar-project.properties`: `sonar.sources` L21, `sonar.tests` L22, coverage report path L28,
  `sonar.coverage.exclusions` L30, `sonar.test.inclusions` L33.

### Reference application (the layout being copied)

`/Users/millsks/UserLocal/apps/src/code/Public-Git/millsks/django-15-factor-base`:

- `src/config/` — `settings/`, `urls.py`, `wsgi.py`, `asgi.py`, `celery_app.py`
- `src/django_service/` — host project: `users/` (concrete `User`), `templates/`, `static/`, `contrib/`
- `tests/` at the repo root; `manage.py` and `pyproject.toml` at the root
- `src/config/settings/base.py:17` — `BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent.parent`
  (four hops); `:20` — `APPS_DIR = BASE_DIR / "src" / "django_service"`, which drives `TEMPLATES["DIRS"]`
  (`:246`), `STATICFILES_DIRS` (`:224`), `MEDIA_ROOT` (`:234`), and `FIXTURE_DIRS` (`:276`).
- `pyproject.toml` — `only-include = ["src"]`, `sources = ["src"]`, and an extended comment documenting the
  hatchling sort/first-matching-prefix behaviour and that adding `src/django_apps` "has to be verified against
  the built wheel, not assumed". That comment is the direct source of AC #3.

### Watch for

- **Editable install path.** `pixi.toml`'s `[pypi-dependencies]` editable entry points at `backend/`. Repoint
  it or `pixi install` fails before any task runs.
- **`BASE_DIR` off-by-one** is the most likely silent defect: it relocates the SQLite DB, `media/`, and
  `staticfiles/` rather than erroring. Hence the explicit test in AC #4.
- **Do not add a `sys.path` insert** in `manage.py`, `wsgi.py`, or `asgi.py` to make imports resolve. The
  reference application treats every such insert as a second import-root declaration site and removes them all;
  the editable install generated from `[tool.hatch.build.targets.wheel]` is the only resolver.
- **Grep the whole repo for `backend/`** rather than trusting the AC list — `.gitignore`, `.dockerignore`,
  `mkdocs.yml`, and `.pre-commit-config.yaml` may all carry paths.

### Why `src/django_apps/inventory/` as a straight move

Renaming the package **and** collapsing the four app labels in one commit makes an already-large diff
impossible to review, and conflates a zero-risk file move with a migration rewrite. Story 21.2 does the
collapse.

### Testing standards

- Unit test under `tests/unit/` asserting the resolved `BASE_DIR`/`APPS_DIR`-derived paths (pure settings
  introspection — no I/O).
- Integration test that builds the wheel and inspects its top-level entries (AC #3).
- No behavioural test changes. Import-path updates only.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.1: Restructure the Repository to a `src/` Layout]
- `backend/pyproject.toml`, `backend/config/settings/base.py`, `pixi.toml`, `Dockerfile`,
  `.github/workflows/ci.yml`, `sonar-project.properties`, `codecov.yml`.
- Reference: `django-15-factor-base` — `src/config/settings/base.py`, `pyproject.toml`, and its
  ARCHITECTURE-SPINE AD-6 (path root) and AD-7 (import roots declared once).
- Downstream: `21-2-collapse-apps-into-inventory-and-establish-django-service.md`.
- Architecture: AD-13 (amended by this epic).

## Dev Agent Record

### Agent Model Used

_(to be filled by the dev agent)_

### Debug Log References

_(to be filled by the dev agent)_

### Completion Notes List

_(to be filled by the dev agent)_

### File List

_(to be filled by the dev agent)_
