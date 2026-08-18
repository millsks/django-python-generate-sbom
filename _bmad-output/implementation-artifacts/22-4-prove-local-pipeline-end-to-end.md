---
baseline_commit: 6feae00
---

# Story 22.4: Prove the Local Pipeline End to End on Both Platforms

Status: review

## Story

As a developer,
I want evidence that a real SBOM job completes locally on SQLite with a real worker,
so that the containerless stack is verified as a working system rather than as a set of green unit tests.

## Acceptance Criteria

1. **A real job completes against a real worker.** — met.
2. **Concurrent writes do not lock the database**, with the cause recorded in settings. — met, and it
   required a real fix.
3. **The verification runs on both platforms** and is visible in CI. — met (the Windows job runs the whole
   suite as of Story 22.3).
4. **The filesystem broker's limits are documented.** — met.

## Dev Agent Record

### Agent Model Used

claude-opus-5[1m] (Claude Opus 5, 1M context)

### Debug Log References

- `pixi run ci` — **exit 0**. **893 passed**, coverage **96.06%**.
- **AC #1**: `tests/integration/test_real_worker_pipeline.py` — 2 tests, ~23s. Starts a genuine
  `celery worker` subprocess against a migrated temp SQLite database, dispatches
  `run_sbom_pipeline.delay(...)` onto the real `filesystem://` broker, and polls until terminal.
  Result: `status=SUCCESS`, a non-null `result_key`, and the SBOM blob present on disk.
- **Proved non-vacuous**: with the worker fixture removed, the same submission ends
  `status=PENDING result_key=None progress=0` — failing both assertions. The test genuinely
  depends on a separate process draining the broker.
- **AC #2**: measured, four threads doing read-then-write against one file —

  | journal_mode | transaction start | result |
  |---|---|---|
  | delete | `BEGIN` (deferred) | **3 of 4 raised "database is locked"** |
  | wal | `BEGIN` (deferred) | **3 of 4 raised "database is locked"** |
  | delete | `BEGIN IMMEDIATE` | 0 errors |
  | wal | `BEGIN IMMEDIATE` | 0 errors |

- Ablation on the committed fix: removing `transaction_mode` fails **3** tests including the
  behavioural one; removing `init_command` (WAL) fails 2; all 7 pass with both.

### Completion Notes List

**The obvious fix was the wrong fix, and the measurement is what caught it.** "SQLite locking →
enable WAL" is the reflex, and WAL changes *nothing* for this failure. The problem is the
**upgrade deadlock**: a deferred transaction takes a SHARED lock to read, then tries to upgrade
to RESERVED to write; if another connection holds RESERVED, SQLite returns `SQLITE_BUSY`
**immediately**, and `busy_timeout` does not apply because waiting could never resolve it. The
fix is `transaction_mode="IMMEDIATE"` (Django 5.1+), which takes the write lock up front so
contenders queue on the timeout instead. Had I shipped WAL alone, the settings comment would
have claimed a safety that did not exist.

WAL is set anyway, for a different and real benefit — readers stop blocking behind an open
writer, which is the everyday `pixi run dev` case with the web process serving pages while the
worker writes phase progress. The timeout is set explicitly because under IMMEDIATE it is what
contenders now queue on.

**My own test was wrong twice before it was right, and the ablation is what exposed it.**
Version 1 used raw `cursor.execute("BEGIN")` and reproduced the deadlock *with the fix in
place* — because Django only emits `BEGIN IMMEDIATE` from its own transaction machinery, so raw
SQL bypasses the setting entirely. Version 2 used `set_autocommit(False)`, which emits no
`BEGIN` at all and passed with the fix **removed** — decorative. Only `transaction.atomic()`
exercises the real path, which meant registering the temp file as a genuine Django database
alias. A consequence worth knowing: **anything in this codebase that opens a transaction with
raw SQL is still exposed.**

**The suite's own database could not test this.** pytest-django runs against an **in-memory**
SQLite database, where `PRAGMA journal_mode` reports `memory` and file locking does not exist —
so an assertion there would have proved nothing. The tests open a real file through Django's own
SQLite backend, configured from `settings.DATABASES`, which checks the project's OPTIONS rather
than that raw `sqlite3` can be coaxed into behaving.

**AC #1 runs offline because of the manifest choice.** A `pixi.lock` is already resolved and its
parser reads the pinned set straight out of the YAML; `requirements.txt` would have shelled out
to `uv pip compile` and needed the network. The analysis phases (4-7) still call OSV/PyPI/NVD and
degrade, which is FR-6.7 working as designed and is why the job reaches SUCCESS regardless.

**Only the database is isolated in the end-to-end test.** `MEDIA_ROOT` and `CELERY_DIR` are
hardcoded to `BASE_DIR` and are not env-overridable. I chose not to add overrides: that would be
changing production configuration for a test's convenience, and both directories are gitignored
and are exactly what `pixi run dev` writes to anyway.

**AC #3 came free from Story 22.3.** The Windows job now runs `pixi run cov`, which is the whole
suite — so both new test modules run on `windows-latest` without any further wiring. The
end-to-end test uses `--pool=solo` there, matching `pixi.toml`'s `[target.win-64]` override;
getting that wrong would have failed on the one platform this epic protects.

### File List

**New (3)**
- `tests/integration/test_sqlite_concurrency.py` (7 tests)
- `tests/integration/test_real_worker_pipeline.py` (2 tests)
- this story file

**Modified (3)**
- `src/config/settings/base.py` — SQLite `OPTIONS`: `transaction_mode`, WAL `init_command`,
  explicit `timeout`, with the measurement recorded in the comment
- `docs/developer/setup.md` — the filesystem broker's limits (AC #4)
- `pyproject.toml` — registered the `slow` marker

## Change Log

| Date | Change |
|---|---|
| 2026-08-18 | Proved the containerless stack end to end and fixed a real concurrency defect on the way. A genuine Celery worker subprocess now completes an SBOM job over the `filesystem://` broker against a temp SQLite database, with the artifact written — verified non-vacuous by removing the worker, which leaves the job PENDING. Measurement showed the reflexive WAL fix does nothing for the read-then-write upgrade deadlock; `transaction_mode="IMMEDIATE"` is what prevents it, and the settings comment records the numbers. Two earlier versions of my own test passed for the wrong reasons (raw `BEGIN` bypasses the setting; bare `set_autocommit` emits no BEGIN) — ablation caught both. Documented the filesystem broker's limits where someone debugging a stuck job will look. `pixi run ci` exit 0; 893 tests at 96.06%. |
