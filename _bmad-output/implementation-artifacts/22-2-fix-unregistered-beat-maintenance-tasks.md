---
baseline_commit: 9f958ea
---

# Story 22.2: Fix the Unregistered Celery Beat Maintenance Tasks

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> **Order:** First story of Epic 22. It is a **confirmed defect already shipping**, not a hardening task, and it
> is independent of the other four — do it before them.

> **This is a bug fix, so the branch prefix is `bugfix/` and the commit type is `fix:`** (global standards §5).

## Story

As a developer running the local stack,
I want the two scheduled maintenance tasks to actually exist in the Celery registry,
so that Beat is not dispatching tasks that every worker rejects.

**Context:** Found during Story 21.1 and carried unfixed through all of Epic 21 because it was out of that
epic's scope. Two shipped features are silently dead: **artifact retention (FR-8.2) never purges**, and the
**parselmouth conda↔PyPI mapping never refreshes**. It mattered less when Beat only ran in a container;
`pixi run dev` now starts Beat on every developer's machine, which is why it belongs in Epic 22.

## Acceptance Criteria

1. **Both scheduled tasks are registered.**
   Given `beat_schedule` names two tasks, when the application starts, then both names are present in
   `app.tasks` and a worker executes them rather than raising `NotRegistered`.
2. **The schedule cannot drift from the registry again.**
   Given the failure was invisible because nothing compared the two, when the story completes, then a test
   asserts every `beat_schedule` entry's `task` resolves in the registry — so adding a third schedule entry
   without importing its module fails the suite.
3. **Both tasks are proven to run.**
   Given the defect hid behind tests that never dispatched them, when the story completes, then each task is
   executed in a test and asserted on its effect, not merely on being importable.
4. **Gate green.** `pixi run ci` exits 0.

## Tasks / Subtasks

- [x] **Task 1 — Register the maintenance module (AC: #1)**
  - [x] Add `maintenance` to the imports in `src/django_apps/inventory/tasks/__init__.py`, following the
        existing `from .sbom_pipeline import run_sbom_pipeline` pattern. Extend `__all__` to match.
  - [x] Verify no circular import results: `maintenance.py` imports `inventory.analysis.services.parselmouth`
        and `inventory.sbom.services`, and `__init__.py` is imported by Celery autodiscovery — confirm
        `pixi run python -c "import inventory.tasks"` succeeds and `pixi run dev` starts.
  - [x] Prove the fix the same way the bug was found (see **Reproduce it first** below), not by reading the diff.
- [x] **Task 2 — Guard against recurrence (AC: #2)**
  - [x] Add a test that iterates `app.conf.beat_schedule.values()` and asserts each `["task"]` is in
        `app.tasks` **after `app.loader.import_default_modules()`**. Calling that loader is the whole point —
        without it the test passes for the wrong reason (see **Traps** below).
  - [x] The failure message should name the offending schedule entry, so a future breakage is self-diagnosing.
- [x] **Task 3 — Execute both tasks (AC: #3)**
  - [x] `refresh_parselmouth_mapping` already has a delegation test
        (`tests/unit/test_maintenance_task.py`); keep it and add the registry-path assertion.
  - [x] `purge_expired_artifacts` has a service-level test
        (`tests/unit/test_artifact_cleanup.py::test_purge_task_delegates_to_the_service`) — confirm it exercises
        the **task**, and add one that runs it end to end against real expired rows, asserting blobs are gone,
        keys nulled, and **job metadata retained** (FR-8.1).
- [x] **Task 4 — Gate (AC: #4)** — `pixi run ci` exits 0.

## Dev Notes

### Reproduce it first — this is the command that found it

```sh
DJANGO_SETTINGS_MODULE=config.settings.local pixi run python -c "
import django; django.setup()
from config.celery_app import app
app.loader.import_default_modules()
reg = set(app.tasks)
sched = {v['task'] for v in app.conf.beat_schedule.values()}
print('MISSING from registry:', sorted(sched - reg) or 'none')"
```

Before the fix this prints **both** task names. After the fix it must print `none`. Use it as the acceptance
check for Task 1 — the bug is invisible in the diff and invisible to the current suite.

### Root cause (verified, 2026-08-18)

`src/config/celery_app.py:18-21` calls `app.autodiscover_tasks()` and then
`app.autodiscover_tasks(["inventory"])`. The second form imports **`inventory.tasks`** — which is a *package*,
so importing it executes `src/django_apps/inventory/tasks/__init__.py`:

```python
"""Celery task modules (pipeline + analysis queues, AD-4)."""

from .sbom_pipeline import run_sbom_pipeline

__all__ = ["run_sbom_pipeline"]
```

That imports `sbom_pipeline` only. `analysis.py` is registered **incidentally**, because
`sbom_pipeline.py:32` does `from inventory.tasks.analysis import (...)` to build the chord. **`maintenance.py`
is imported by nothing**, so its two `@shared_task`s are never registered.

Confirmed registry contents after `import_default_modules()` — 9 tasks, none from `maintenance`:

```
inventory.tasks.analysis.check_version_currency
inventory.tasks.analysis.classify_licenses
inventory.tasks.analysis.scan_vulnerabilities
inventory.tasks.sbom_pipeline.aggregate_analysis_results
inventory.tasks.sbom_pipeline.detect_and_parse_manifest
inventory.tasks.sbom_pipeline.generate_sbom_document
inventory.tasks.sbom_pipeline.persist_artifacts
inventory.tasks.sbom_pipeline.resolve_transitive_deps
inventory.tasks.sbom_pipeline.run_sbom_pipeline
```

### Why the existing tests pass while production is broken

This is the important lesson, and the reason AC #2 is worded around the *registry* rather than the *import*.
`tests/unit/test_maintenance_task.py` starts with:

```python
from inventory.tasks.maintenance import refresh_parselmouth_mapping
```

A direct import **registers the task for that test session**, so `.apply()` works and the test passes. Nothing
in production performs that import. Any test that reaches a task by importing its module can never detect this
class of bug — only a test that inspects the registry the way Beat and the worker do will.

### Traps

- **`app.tasks` is lazy.** Without `app.loader.import_default_modules()` the registry is nearly empty and a
  naive guard test passes vacuously — it would "pass" today, against the bug. Call the loader, and consider
  asserting the registry is non-empty first so a future change to Celery's loading cannot silently hollow the
  test out.
- **Do not fix this in `celery_app.py` with `app.conf.imports`.** It would work, but it splits task
  registration across two places (autodiscovery *and* an imports list), and the next module added would face
  the same coin-flip. `inventory/tasks/__init__.py` is already the file that decides what the package exposes;
  keep one answer to "how does a task module get registered".
- **`app` is module-level in `celery_app.py`.** Importing it in a test is safe (no settings are touched at
  import time — see the module comment at `:1-8`), but it is a **shared singleton**: if a test mutates
  `app.conf.beat_schedule`, restore it, or later tests inherit the change.
- **Story 21.24 changed nothing here**, but note `purge_expired_artifacts` writes to jobs across **all** orgs
  by design (it is a system sweep, not a request), so it does not go through `get_request_org`. Do not "fix"
  that into an org-scoped call.
- **Multi-line `{# … #}` template comments are a trap in this codebase** — irrelevant here (no templates), but
  it is the house rule if you touch one.

### Queue routing — a discrepancy to leave alone

`refresh_parselmouth_mapping` is declared `@shared_task(queue="analysis")` while `purge_expired_artifacts` is
`queue="pipeline"`. AD-4 says "Celery Beat cleanup tasks (FR-8.2) also route to the `pipeline` queue" — the
purge complies; the mapping refresh is not cleanup, so `analysis` is a defensible choice. Locally
`pixi run worker` drains **both** queues, so either works; in the container topology `worker-analysis` picks it
up. **Do not re-route it as part of this story** — that is an AD-4 interpretation question, not a bug. Flag it
if you disagree.

### Files being modified — current state

- **`src/django_apps/inventory/tasks/__init__.py`** (UPDATE) — 4 lines; re-exports `run_sbom_pipeline`. This is
  the whole fix surface.

  **Verified: nothing actually consumes that re-export.** `inventory/sbom/services.py:167` lazy-imports from
  the *module* (`from inventory.tasks.sbom_pipeline import run_sbom_pipeline`, Story 21.9, to dodge a circular
  import), and the two pipeline test modules do `from inventory.tasks import sbom_pipeline` — the submodule, not
  the name. So the existing `from .sbom_pipeline import run_sbom_pipeline` line exists **only** as the
  side-effecting import that registers those tasks.

  That is worth knowing before you edit it two ways: leaving it alone is safe, and if you find the
  re-export-plus-`__all__` shape misleading (it reads like a public API and is really a registration hook), say
  so in the completion notes rather than quietly restyling it — but **do not remove it**, or you trade this bug
  for the same bug in `sbom_pipeline`.
- **`src/config/celery_app.py`** (READ, probably UNCHANGED) — holds `beat_schedule` at `:23-34`. The guard test
  reads it; the fix should not need to edit it.
- **`src/django_apps/inventory/tasks/maintenance.py`** (READ, UNCHANGED) — the two tasks are correct as
  written; they were simply never imported.
- **`tests/unit/test_maintenance_task.py`** (UPDATE) — 1 test.
- **`tests/unit/test_artifact_cleanup.py`** (UPDATE) — 8 tests, including
  `test_purge_task_delegates_to_the_service`.

### Testing standards

- `tests/unit/` — no I/O, no network. `pixi run test` in the inner loop; `pixi run ci` is the gate
  (coverage ≥90%, currently 96.02%).
- Celery runs **eager** under `config.settings.test`, so `.apply()` executes inline. That is fine for AC #3, but
  it is *why* AC #1 needs the registry assertion rather than an execution assertion.
- FR-8.1: a purge deletes **blobs** and nulls **keys**; the `SBOMJob` row and its metadata are retained. Assert
  the retention, not only the deletion — the inverse assertion is the one that catches an over-eager sweep.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 22.2: Fix the Unregistered Celery Beat Maintenance Tasks]
- Architecture: **AD-4** (two Celery queues; Beat cleanup → `pipeline`), **AD-10** (`@shared_task` only, no
  Celery app import in task modules), **AD-6** (artifact blobs in S3/MinIO only), **FR-8.1/8.2** (job records
  retained; scheduled cleanup).
- Code: `src/config/celery_app.py`, `src/django_apps/inventory/tasks/{__init__,maintenance,sbom_pipeline}.py`,
  `src/django_apps/inventory/sbom/services.py` (`purge_expired_artifacts`).
- Tests: `tests/unit/test_maintenance_task.py`, `tests/unit/test_artifact_cleanup.py`.
- Discovered in: `_bmad-output/implementation-artifacts/21-1-restructure-to-src-layout.md` (recorded as
  "pre-existing; needs its own bug story" and carried through Stories 21.2–21.24).

## Project Structure Notes

- No new packages, modules, or directories. The fix is an import line and its `__all__` entry.
- One new test may live in an existing module rather than a new file — prefer extending
  `test_maintenance_task.py` over creating a near-duplicate module.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. **848 passed**, coverage **96.03%**, floor unchanged at 90%.
- **6 new tests** in `tests/unit/test_beat_schedule_registry.py`.
- Registry before the fix: **9** `inventory.*` tasks, both scheduled names missing. After:
  **11**, and the story's reproduction command prints `MISSING from registry: none`.
- **The guard was proven to bite.** With the fix reverted, **3** of the 6 fail
  (`test_every_scheduled_task_resolves_in_the_registry` plus both purge tests); with it
  restored, all 6 pass.
- `pixi run dev` starts web + worker + beat with the fix in place, and the log contains no
  `NotRegistered`.

### Completion Notes List

**Red before green, and the red was the real bug.** The guard test was written first and
failed by naming both offending schedule entries — `refresh-parselmouth-mapping` and
`purge-expired-artifacts` — which is the exact form of the defect. Only then was the import
added.

**The fix registers `analysis` explicitly too, even though it already worked.** It was being
registered *incidentally*, because `sbom_pipeline` imports it to build the chord. Relying on
that side effect is how `maintenance` came to be missed in the first place: two of three task
modules were registered for two different reasons and nobody could see which. All three are now
listed for one reason, and the module docstring says plainly that these imports **are task
registration, not a public API** — because that is not obvious from reading them.

**The re-export was kept deliberately.** Story context flagged that nothing consumes
`from inventory.tasks import run_sbom_pipeline` (call sites import the submodule instead), so it
looks like removable dead code. Removing it would have traded this bug for the same bug in
`sbom_pipeline`. It stays, and `__all__` now lists the modules so the file's purpose reads
correctly.

**Two tests initially failed with `NotRegistered` — the production symptom, reproduced in a
test.** Looking up `app.tasks[...]` by name only works after discovery has run, which a worker
does at boot and a test does not. Rather than switch to a direct import (which would have
quietly reintroduced the blind spot the whole story is about), an autouse fixture calls
`import_default_modules()` — so every lookup travels the same path Beat's dispatch-by-name
does. That is the detail that makes these tests capable of catching a regression.

**AC #3 asserts effects on both sides of the purge.** Expired blobs are gone and their keys
nulled (FR-8.2, AD-6), *and* the `SBOMJob` row, status, and `summary_stats` survive (FR-8.1).
There is also an inverse test proving an unexpired job is left alone — without it, a sweep that
deleted everything would pass.

**Two things I left alone, as the story directed.** `refresh_parselmouth_mapping` stays on the
`analysis` queue (an AD-4 interpretation question, not a bug), and `purge_expired_artifacts`
stays a cross-org sweep (it is a system task, not a request).

**Unrelated blocker cleared to reach a green gate.** `test_the_frontend_directory_is_gone`
failed because a `frontend/` directory was still on disk — a working-tree leftover from
switching to `main` and back, containing only `node_modules/`, `dist/`, and `coverage/` with
zero tracked files. Removed. A comparable pre-21.1 `backend/` leftover (`.coverage`,
`.pytest_cache`, a stale wheel, `__pycache__` — also nothing tracked) is **still present**; it
breaks nothing and removing it was outside this story.

### File List

**New (1)**
- `tests/unit/test_beat_schedule_registry.py` (6 tests)

**Modified (2)**
- `src/django_apps/inventory/tasks/__init__.py` — imports `analysis`, `maintenance`, and
  `sbom_pipeline`; docstring explains that these imports are registration
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, and this story file

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Registered the maintenance task module so Beat's two scheduled tasks exist in the Celery registry. `autodiscover_tasks(["inventory"])` imports the `inventory.tasks` package, so its `__init__.py` decides what is registered — and it imported only `sbom_pipeline`; `analysis` worked incidentally via the chord import, and `maintenance` not at all, leaving artifact retention (FR-8.2) and the parselmouth refresh silently dead. All three modules are now imported for one stated reason. Added `test_beat_schedule_registry.py`, which asks the registry the question Beat asks rather than importing the task module — the import is what masked the bug — and proved it bites by reverting the fix (3 of 6 fail). Both tasks are executed **by name from the registry** with effect assertions on each side of the purge: blobs deleted and keys nulled, job metadata retained, unexpired jobs untouched. `pixi run ci` exit 0; 848 tests at 96.03%. |
