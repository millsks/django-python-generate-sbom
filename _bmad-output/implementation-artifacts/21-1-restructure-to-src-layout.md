---
baseline_commit: e5778dee2a521120a337ca517f509815653894da
---

# Story 21.1: Restructure the Repository to a `src/` Layout

Status: review

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

- [x] **Task 1 — Move the tree (AC: #1)** — `git mv` `backend/config` → `src/config`,
  `backend/generate_sbom` → `src/django_apps/inventory`, `backend/tests` → `tests`, and
  `backend/{manage.py,pyproject.toml}` → repo root. Create `src/django_service/` (package, with
  `__init__.py`). Use `git mv` so history is preserved and the diff reads as renames.
- [x] **Task 2 — Make `src/django_apps/` a path root (AC: #2)** — Ensure it has **no** `__init__.py`. Set
  `only-include = ["src"]` and `sources = ["src", "src/django_apps"]`.
- [x] **Task 3 — Wheel verification test (AC: #3)** — Build the wheel and assert its top-level entries. This
  is the AC most likely to fail first; treat a `django_apps/inventory` result as the expected failure mode and
  resolve it in `sources`, not with a `sys.path` insert.
- [x] **Task 4 — `BASE_DIR` / `APPS_DIR` (AC: #4)** — Correct the `parent` chain, introduce `APPS_DIR`, and add
  a unit test asserting the derived paths.
- [x] **Task 5 — Repoint packaging + tool config (AC: #5)** — The six settings in `pyproject.toml`.
- [x] **Task 6 — Strip `cwd` from pixi tasks (AC: #6)** — All 24 occurrences. Smoke-run each task group.
- [x] **Task 7 — Dockerfile + CI + Sonar + Codecov (AC: #7)** — Update every `backend/` path reference.
- [x] **Task 8 — Verify the SPA still works (AC: #8)** — `pixi run fe-build`, `collectstatic`, then load each
  SPA route against `pixi run runserver`.
- [x] **Task 9 — Gate (AC: #9)** — `pixi run ci` to green; confirm the diff contains no assertion changes.

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

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. precommit / build / check / lint / fmt-check / security / cov /
  fe-lint / fe-typecheck / fe-cov / fe-build / docs-build all pass.
- Backend: **417 passed**, coverage **95.89%** (gate 90%). Frontend: **223 passed** across 39 files.
- `mypy src` — clean over **90** source files.
- Built wheel top-level entries: `['config', 'django_service', 'generate_sbom-0.1.0.dist-info', 'inventory']`.
- Wheel built with the story's hypothesised array form, for contrast:
  `['config', 'django_apps', 'django_service', 'generate_sbom-0.1.0.dist-info']` — no `inventory`.
- Live route check against `runserver` (port 8111): `/`, `/login`, `/register`, `/jobs`,
  `/organizations` → 200 (SPA index, 484 bytes each); `/admin/` → 302; `/health/` → 200
  `{"status": "ok"}`; `/api/docs/` → 200; `/api/schema/` → 200 (41 KB);
  `/api/v1/{sbom/jobs,orgs,auth/me}/` → 401 (auth required, i.e. routed and reachable).
- `collectstatic` → 177 files copied, 334 post-processed, into `./staticfiles/`.
- `celery beat` → `db -> .celery/celerybeat-schedule`; `celery worker` → binds `pipeline` + `analysis`.
- `git diff --cached -M`: **70 pure renames + 71 renamed-and-edited**, so history is preserved.

### Completion Notes List

**AC #3 falsified AC #2's literal `sources` value — this is the story's headline finding.**
The array form the reference application flagged as unverified, `sources = ["src", "src/django_apps"]`,
**does not work**. Verified against hatchling rather than reasoned about:
`BuilderConfig.sources` ends with `dict(sorted(sources.items()))` and
`get_distribution_path` returns on the **first** `startswith` match. `normalize_relative_directory`
yields `'src/'` and `'src/django_apps/'`, and `'src/' < 'src/django_apps/'`, so every app path is
rewritten by `'src/'` alone and the app ships as `django_apps/inventory`. Building the wheel both
ways confirms it (see Debug Log). Under the array form `import inventory` fails outright and the whole
suite cannot even be collected.

Resolved **in `sources`** as Task 3 directs — not with a `sys.path` insert — by switching to the
**mapping form**, whose keys do not prefix-collide:

```toml
[tool.hatch.build.targets.wheel.sources]
"src/config" = "config"
"src/django_service" = "django_service"
"src/django_apps" = "."
```

This also keeps editable installs correct with no special-casing: hatchling derives the `.pth` roots
from the rewritten distribution paths, producing `src` and `src/django_apps`. `force-include` was
considered and **rejected** — `build_editable_*` copies force-included files into the wheel, so the app
would be a frozen copy in site-packages shadowing the working tree. `dev-mode-dirs` alone was rejected
too: it fixes only the editable install and leaves the published wheel wrong.
**AC #2's `sources` line should be amended to the mapping form.**

**Test assertions changed (AC #9 asked for none beyond import paths) — three, each forced by another AC:**
1. `tests/unit/test_dev_runner_config.py` × 3 — `assert task["cwd"] == "backend"` is unsatisfiable once
   AC #6 removes `cwd`. Inverted to `assert "cwd" not in task`, which is stronger: it stops a stray `cwd`
   from creeping back.
2. `tests/unit/test_{dev_runner_config,manifest_format_consistency}.py` — `parents[3]` → `parents[2]`.
   Path derivation, not behaviour: the files lost a directory level.
3. `tests/unit/test_settings_celery.py` — renamed `test_local_celery_dir_is_under_backend_base` →
   `..._under_base_dir` and fixed its comment. Assertion body untouched.

**A sed over-rename I introduced and reverted — worth a reviewer's eye.**
`generate_sbom` → `inventory` also hit the pipeline **task function** `generate_sbom_document`
(→ `inventory_document`), silently renaming the Celery task and desynchronising it from
`beat_schedule`. Caught by inspecting the live task registry, not by the suite — every test was renamed
in lockstep, so all 417 stayed green while the task name was wrong. Reverted; per-file occurrence counts
now match `HEAD` exactly (1/2/3/2/1/1/4/9/17 across the 9 affected files). `generate_sbom_document` was
the **only** identifier where `generate_sbom` was a substring rather than the package prefix (verified
by regex over `HEAD`).

**Three scope widenings, each a consequence of the move, each with fallout fixed:**
- `check`: `mypy generate_sbom` → `mypy src`. `config/` had **never** been type-checked. Surfaced 3
  pre-existing errors: `environ` has no `py.typed` (added to `[[tool.mypy.overrides]]`), and
  `configure_structlog` was unresolvable in `local.py`/`production.py` because strict
  `no_implicit_reexport` does not re-export a plain import through `from .base import *`. Fixed with the
  redundant-alias idiom (`import X as X`) in `base.py` — deliberately chosen so the `config` → app import
  stays in the **one** place that already had it, rather than adding two more instances of a gap the epic
  has already recorded for a later epic.
- `security`: `bandit -r generate_sbom` → `bandit -r src`. Surfaced B104 on `local.py`'s
  `ALLOWED_HOSTS = [..., "0.0.0.0"]` — a false positive (a Host-header allowlist, not a bind address, in
  LOCAL-only settings). Suppressed **inline** rather than via `[tool.bandit] skips` so a genuine bind-all
  elsewhere still fails the gate. Bandit then emits a cosmetic `nosec encountered ... but no failed test`
  warning because `-ll` filters the finding before reconciling the marker; `Medium: 0`, gate green.
- `lint` / `fmt`: ruff was previously scoped by `cwd = "backend"`. From the repo root `ruff check .`
  swept vendored BMad/agent scripts — **354 errors** across 23 files we do not own. Added
  `extend-exclude = ["_bmad", "_bmad-output", ".claude", ".agents"]`, mirroring the existing
  `.pre-commit-config.yaml` exclude so task, hook, and editor all agree.

**Coverage now measures `src` (config included) and still clears the gate at 95.89%.**

**Pre-existing defect found, deliberately NOT fixed here (out of scope for a mechanical move):**
the two `beat_schedule` entries — `inventory.tasks.maintenance.{refresh_parselmouth_mapping,
purge_expired_artifacts}` — are **not in the Celery task registry** at runtime. `inventory/tasks/__init__.py`
imports only `sbom_pipeline`, no `INSTALLED_APPS` entry has a `tasks` module for
`autodiscover_tasks()` to find, and nothing imports `maintenance`, so Beat would dispatch an
unregistered task. Confirmed pre-existing: `tasks/__init__.py` is byte-identical to `HEAD` and
`celery_app.py` differs from `HEAD` only by the package rename. The unit tests pass because they import
the module directly, which registers it. **Needs its own bug story.**

**Deferred to Story 21.21 (documentation reconciliation), as the epic ordered:** narrative `backend/`
path references in `README.md` (tree diagram, L75/L83) and `docs/` (`project-layout.md`,
`setup.md`, `architecture.md`, `testing.md`, `pipeline.md`, the OpenShift pages). Only
**functional** references were fixed here — `mkdocs.yml` griffe `paths`, the `code-reference.md`
mkdocstrings identifiers (both required for `docs-build --strict`), and the one executable README
command (`pixi run python backend/manage.py` → `manage.py`). Because the epic merges big-bang at 21.23,
no stale prose reaches `main`.

**Also done, beyond the AC list but required by the move:** `.gitignore` (`.celery/`, `media/`, plus
`staticfiles/` which was never ignored and is now a root-level artifact), `.dockerignore`,
`.pre-commit-config.yaml` `files:` patterns, `.github/labeler.yml`, `.github/workflows/release.yml`
(wheel now lands in root `dist/`), `.env.local.example`, and ruff `per-file-ignores` (the old
`config/settings/*` patterns no longer matched under `src/`). The Dockerfile now copies
`pyproject.toml` + `manage.py` + `src/` before `pixi install --locked`, preserving the
editable-install ordering AC #7 calls out.

**No `sys.path` inserts were added** to `manage.py`, `wsgi.py`, or `asgi.py`, and pytest's
`pythonpath` was **removed** rather than repointed — the editable install is the sole import-root
resolver (reference AD-7).

**Local artifacts relocated** (all git-ignored, no data lost): `db.sqlite3`, `media/`, and `.celery/`
moved from `backend/` to the repo root to match the new `BASE_DIR`; stale `backend/` tool caches
(`.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.coverage`, `dist/`) removed. `backend/` no longer exists.

### File List

**New (4)**
- `pyproject.toml` (repo root; replaces `backend/pyproject.toml`)
- `src/django_service/__init__.py`
- `tests/unit/test_settings_paths.py` (AC #4)
- `tests/integration/test_wheel_layout.py` (AC #3)

**Deleted (1)**
- `backend/pyproject.toml`

**Moved (141 total: 70 pure renames, 71 renamed-and-edited)**
- `backend/config/` → `src/config/`
- `backend/generate_sbom/` → `src/django_apps/inventory/`
- `backend/tests/` → `tests/`
- `backend/manage.py` → `manage.py`

**Modified in place (16)**
- `pixi.toml` (24 × `cwd = "backend"` removed; editable path `./backend` → `.`; `mypy src`,
  `bandit -r src`, `--cov=src`)
- `pixi.lock` (regenerated for the editable-path change)
- `Dockerfile`, `.dockerignore`, `.gitignore`, `.pre-commit-config.yaml`
- `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `.github/labeler.yml`
- `sonar-project.properties`, `codecov.yml`
- `mkdocs.yml`, `docs/developer/code-reference.md`
- `.env.local.example`, `README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Notable edits inside moved files**
- `src/config/settings/base.py` — `BASE_DIR` 4 hops, new `APPS_DIR`, `FRONTEND_DIST` drops its
  `.parent`, redundant-alias re-export of `configure_structlog`, `INSTALLED_APPS`/DRF paths → `inventory.*`
- `src/config/settings/local.py` — `.celery` comment, B104 inline suppression
- `src/config/celery_app.py` — app name + autodiscover + `beat_schedule` task paths → `inventory.*`
- `src/django_apps/inventory/{users,manifests}/migrations/0001_initial.py` — import paths only
  (migration graph and app labels untouched)
- `tests/unit/test_dev_runner_config.py`, `tests/unit/test_manifest_format_consistency.py`,
  `tests/unit/test_settings_celery.py` — see Completion Notes

## Change Log

| Date | Change |
|---|---|
| 2026-08-17 | Restructured the repository to the `src/` layout (`src/config`, `src/django_service`, `src/django_apps/inventory`; `tests/`, `manage.py`, `pyproject.toml` at the root). Renamed the app package `generate_sbom` → `inventory`, imported unqualified via a hatchling `sources` **mapping** after proving the array form is shadowed. Stripped all 24 `cwd = "backend"` pixi entries and repointed Docker/CI/Sonar/Codecov/mkdocs. Added AC #3 wheel-layout and AC #4 settings-path tests. `pixi run ci` exit 0; 417 backend + 223 frontend tests pass at 95.89% coverage. |
