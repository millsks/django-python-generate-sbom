# Story 20.4: Cross-Platform Async Worker (Filesystem Broker + DB Result Backend)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** Implement **after Story 20.3** (it owns the local dev settings module this config lives in).

> **⚠ SIGN-OFF GATE.** This story **proposes a new dependency — `django-celery-results`** (the SQLite/DB
> result backend). Adding a runtime dependency requires the **user's explicit sign-off at implementation time**
> (Control Constraints §7). The story proposes; do not add the dep until the user approves.

## Story

As a developer,
I want the local Celery broker and result backend to run without Redis, on both macOS and Windows,
so that a **real, separate** Celery worker processes SBOM jobs locally — mirroring OCP — with no container.

## Acceptance Criteria

1. **Filesystem broker (no Redis).**
   Given `base.py` sets `CELERY_BROKER_URL = REDIS_URL` (default `redis://localhost:6379/0`, L148–149), when
   the local dev settings load, then the broker is a Kombu **`filesystem://`** transport with
   `broker_transport_options` pointing `data_folder_in`/`data_folder_out` at a **portable, repo-local,
   git-ignored** directory (e.g. `backend/.celery/broker/`) that exists on both macOS and Windows — no Redis
   process is required for local dev.
2. **DB result backend via django-celery-results (SIGN-OFF).**
   Given `base.py` sets `CELERY_RESULT_BACKEND = REDIS_URL` (L150) and there is currently **no**
   `django-celery-results` in the project, when the user approves the dependency, then the local dev settings
   set `CELERY_RESULT_BACKEND = "django-db"`, `django_celery_results` is added to `INSTALLED_APPS`, the
   dependency is added to `pixi.toml`, and its migrations are applied against the local SQLite DB — so results
   persist without Redis. **If sign-off is withheld, this story stops at the proposal.**
3. **Windows-compatible worker pool.**
   Given the Celery prefork pool is Unix-only, when the worker runs on Windows (`win-64`), then it uses
   `--pool=solo` (or `threads`) instead of prefork `-c 4`; the macOS/Linux worker keeps prefork. This is wired
   via the per-platform pixi task overrides in Story 20.5 — this story defines the required pool per OS and
   confirms the tasks resolve to it.
4. **Portable beat schedule path.**
   Given `beat` writes `-s /tmp/celerybeat-schedule` (`pixi.toml` L151 — a POSIX-only path), when beat runs
   locally, then the schedule file lives at a **portable, git-ignored** location (e.g.
   `backend/.celery/celerybeat-schedule`) that resolves on Windows — no hardcoded `/tmp`. (The two existing
   beat entries in `celery_app.py` L23–34 are unchanged.)
5. **Eager mode stays the test path.**
   Given the test suite must stay offline (no broker/Redis), when tests run, then Celery executes **eagerly**
   for tests — `CELERY_TASK_ALWAYS_EAGER = True` (with `CELERY_TASK_EAGER_PROPAGATES = True`) is set for the
   test configuration. NOTE: this flag is **not currently set anywhere** (tests today assume live infra); this
   story makes eager the explicit test path so the filesystem broker never leaks into the unit suite, and the
   result backend under eager does not require a live DB round-trip beyond the local SQLite.
6. **A real worker drains a real job + gate green.**
   Given the filesystem broker + DB result backend, when a worker is started and an SBOM job is submitted
   locally (containerless), then the job is picked up by the **separate** worker process and completes through
   the pipeline (mirroring OCP's real-worker model, not eager), and `pixi run ci` is green (backend coverage
   ≥90%) with the eager test path intact.

## Tasks / Subtasks

- [ ] **Task 0 — Sign-off (AC: #2)** — Propose `django-celery-results` to the user; do not add it to
  `pixi.toml` or `INSTALLED_APPS` until approved.
- [ ] **Task 1 — Filesystem broker (AC: #1)** — In the local dev settings, set
  `CELERY_BROKER_URL = "filesystem://"` and `CELERY_BROKER_TRANSPORT_OPTIONS` with portable in/out/processed
  folders under a git-ignored `backend/.celery/broker/`; ensure the dirs are created (or documented as created
  on first run).
- [ ] **Task 2 — DB result backend (AC: #2)** — After sign-off: add `django-celery-results` to `pixi.toml`,
  add `django_celery_results` to `INSTALLED_APPS`, set `CELERY_RESULT_BACKEND = "django-db"`, run
  `makemigrations`/`migrate` (its migrations) against local SQLite.
- [ ] **Task 3 — Pool + beat path (AC: #3, #4)** — Define the Windows `--pool=solo`/`threads` vs. macOS/Linux
  prefork requirement (consumed by Story 20.5's per-platform tasks); relocate the beat schedule to a portable
  git-ignored path; add `backend/.celery/` to `.gitignore`.
- [ ] **Task 4 — Eager test path (AC: #5)** — Set `CELERY_TASK_ALWAYS_EAGER = True` +
  `CELERY_TASK_EAGER_PROPAGATES = True` for the test configuration so the unit suite never touches the
  filesystem broker; add a test asserting eager is on under the test settings.
- [ ] **Task 5 — Real-worker verification + gate (AC: #6)** — Start a separate worker against the filesystem
  broker, submit a job, confirm it drains and persists a result; run `pixi run ci` to green.

## Dev Notes

### Grounded facts (verified)

- `base.py` L147–158: `REDIS_URL` default `redis://localhost:6379/0`; `CELERY_BROKER_URL` = `CELERY_RESULT_BACKEND`
  = `REDIS_URL`; `CELERY_TASK_DEFAULT_QUEUE = "pipeline"`; soft/hard limits 1800/2100s.
- `celery_app.py`: `config_from_object("django.conf:settings", namespace="CELERY")` (L17) — so broker/backend
  come entirely from the `CELERY_*` Django settings; `autodiscover_tasks(["generate_sbom"])` (L21); two beat
  entries (`refresh_parselmouth_mapping` weekly, `purge_expired_artifacts` nightly, L23–34).
- `pixi.toml`: `beat` = `celery -A config.celery_app beat -s /tmp/celerybeat-schedule` (L150–152);
  `worker-pipeline` = `celery … worker -Q pipeline -c 4` (L142–144); `worker-analysis` = `… -Q analysis -c 4`
  (L146–148). `-c 4` is prefork with no `--pool` → needs `--pool=solo` on Windows.
- `django-celery-results` is **absent** today; the result backend is Redis (`base.py` L150). Adding it is a
  new dep → sign-off.
- `CELERY_TASK_ALWAYS_EAGER` is **not set anywhere** (verified — only doc references exist); `conftest.py`
  files add no eager config. Tests today assume live infra. This story makes eager explicit for the test path.

### Why filesystem broker + DB result backend (fixed decision)

Keeping Celery (not swapping to a synchronous path) means local mirrors OCP: a **real separate worker**. Kombu's
`filesystem://` transport removes the Redis broker; `django-celery-results` (`django-db`) removes the Redis
result backend — both cross-platform and containerless. Eager mode stays **only** for the test suite so tests
run offline.

### Portable paths (Windows)

`/tmp` does not exist on Windows. Use a repo-relative, git-ignored `backend/.celery/` directory for both the
filesystem broker folders and the beat schedule. Prefer `Path(BASE_DIR, ".celery", …)` construction so the
path is OS-correct.

### Testing standards

- Unit: assert `CELERY_TASK_ALWAYS_EAGER` is `True` under the test settings and the local settings select the
  `filesystem://` broker; keep the unit suite fully offline.
- Integration (optional, `@pytest.mark.integration`): a real worker draining a job may be exercised as an
  integration test using `tmp_path` broker folders — not in the fast unit suite.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.4: Cross-Platform Async Worker (Filesystem Broker + DB Result Backend)]
- `backend/config/settings/base.py` (L147–158), the local dev settings module (Story 20.3),
  `backend/config/celery_app.py` (L17, L21, L23–34), `pixi.toml` (L142–152), `.gitignore`.
- Upstream: `20-3-containerless-local-dev-settings.md`. Downstream:
  `20-5-cross-platform-pixi-tasks-and-dev-runner.md` (consumes the per-OS pool + portable beat path).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Opus 4.8, 1M context)

### Debug Log References

- Real-worker drain verified locally (AC #6): a separate `celery … worker -Q pipeline
  --pool=solo` process connected to `transport: filesystem://localhost//`, consumed a
  `.delay()`-dispatched task, and persisted the result row in the `django_celery_results`
  `TaskResult` table — final `state: SUCCESS`, `db status: SUCCESS`.
- Kombu footgun: the `filesystem://` transport WRITES messages to `data_folder_out` and
  READS from `data_folder_in`, so both MUST point at the SAME directory or a producer and a
  consumer never meet (first drain hung at PENDING with split `in/`/`out` dirs). Also pinned
  `control_folder` under `.celery/` — it otherwise defaults to a `control/` dir in the CWD.

### Completion Notes List

- **AC #1 (filesystem broker):** `local.py` sets `CELERY_BROKER_URL = "filesystem://"` with
  `CELERY_BROKER_TRANSPORT_OPTIONS` pointing `data_folder_in`/`data_folder_out` at a single
  shared, git-ignored `backend/.celery/broker/messages/` dir (plus `processed_folder` and
  `control_folder`), all built with pathlib so they resolve on Windows (no `/tmp`) and are
  created on import.
- **AC #2 (DB result backend, SIGN-OFF):** user approved `django-celery-results`. Added to
  `pixi.toml` `[dependencies]` (`>=2.5`, noarch — resolves on all 4 platforms incl. win-64),
  `django_celery_results` added to base `INSTALLED_APPS`, `local.py` sets
  `CELERY_RESULT_BACKEND = "django-db"`. Its migrations ship in the package (`makemigrations
  --check` → "No changes detected"; nothing to commit) and apply cleanly to local SQLite.
- **AC #3 (Windows pool):** documented the per-OS pool requirement at the worker tasks in
  `pixi.toml` (Unix prefork `-c 4` vs. Windows `--pool=solo`); the per-platform `[target.*]`
  task overrides are wired by Story 20.5. Verified the worker runs under `--pool=solo`.
- **AC #4 (portable beat):** `beat` task now uses `-s .celery/celerybeat-schedule` (cwd
  `backend`) instead of POSIX-only `/tmp/celerybeat-schedule`; `backend/.celery/` gitignored.
- **AC #5 (eager for tests):** new `config/settings/test.py` inherits `local` and sets
  `CELERY_TASK_ALWAYS_EAGER`/`CELERY_TASK_EAGER_PROPAGATES = True`; pytest now points at
  `config.settings.test`, so the unit suite never touches the filesystem broker. Five task
  tests that inspect a captured FAILURE `.apply()` result were pinned to `throw=False`
  (eager-propagation would otherwise re-raise out of `apply()`); `test_settings_celery.py`
  asserts eager-on + the filesystem broker + django-db backend + prod-Redis-untouched.
- **AC #6 (real-worker drain + gate):** see Debug Log. `pixi run ci` green (backend 96.03%
  coverage, 394 tests; frontend 223 tests).
- **Prod/container path untouched:** `base.py` still sets `CELERY_BROKER_URL` /
  `CELERY_RESULT_BACKEND` to `REDIS_URL`; `production.py` unchanged. Only `local.py` (dev)
  and the test settings diverge.

### File List

- `backend/config/settings/base.py` — add `django_celery_results` to `INSTALLED_APPS`
- `backend/config/settings/local.py` — filesystem broker + django-db result backend
- `backend/config/settings/test.py` — NEW: eager Celery for the test path
- `backend/pyproject.toml` — pytest `DJANGO_SETTINGS_MODULE = config.settings.test`
- `backend/tests/unit/test_settings_celery.py` — NEW: containerless-Celery settings tests
- `backend/tests/unit/test_pipeline_orchestration.py` — pin `throw=False` on 4 failure tests
- `backend/tests/unit/test_sbom_generation.py` — pin `throw=False` on the phase-3 failure test
- `pixi.toml` — add `django-celery-results`; portable beat path; per-OS worker-pool docs
- `pixi.lock` — re-solved (django-celery-results across all 4 platforms incl. win-64)
- `.gitignore` — ignore `backend/.celery/`
