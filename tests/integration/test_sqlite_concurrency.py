"""Story 22.4 AC #2: concurrent writers must not hit "database is locked".

Local development runs **three processes against one SQLite file** — `pixi run dev` starts web,
worker, and beat — and SQLite allows a single writer. This is the failure most likely to bite a
developer who has no container fallback, and it appears under load rather than on the first run.

**The obvious fix is not the fix.** Measured against a real file, four concurrent read-then-write
transactions:

    journal_mode=delete  BEGIN (deferred)   -> 3 of 4 raised "database is locked"
    journal_mode=wal     BEGIN (deferred)   -> 3 of 4 raised "database is locked"
    journal_mode=delete  BEGIN IMMEDIATE    -> 0 errors
    journal_mode=wal     BEGIN IMMEDIATE    -> 0 errors

WAL alone changes nothing here. The failure is the *upgrade deadlock*: a deferred transaction
takes a SHARED lock to read, then tries to upgrade to RESERVED to write; if another connection
holds RESERVED, SQLite returns `SQLITE_BUSY` **immediately** and `busy_timeout` does not apply,
because waiting could never resolve it. `BEGIN IMMEDIATE` takes the write lock up front, so
contenders queue on the timeout instead of deadlocking. WAL is still set, for the separate
benefit that readers stop blocking behind an open writer.

**`transaction_mode` only covers Django-managed transactions.** Django emits
`BEGIN {transaction_mode}` from `_start_transaction_under_autocommit()`, so `transaction.atomic()`
and `set_autocommit(False)` get `IMMEDIATE` — but hand-written `cursor.execute("BEGIN")` does
not, and still deadlocks. These tests drive Django's own transaction machinery for exactly that
reason; an earlier draft used raw SQL and reproduced the deadlock *with the fix in place*, which
was the test being wrong rather than the setting. Anything in this codebase that opens a
transaction by raw SQL would be back in the failure mode.

**Why these tests build their own connection.** pytest-django runs the suite against an
**in-memory** SQLite database (`TEST["NAME"]` is unset, so Django uses `:memory:`), where
`PRAGMA journal_mode` reports `memory` and file-level locking does not exist. Asserting
contention there would prove nothing. So the behavioural tests open a real file-backed database
through **Django's own SQLite backend**, configured from `settings.DATABASES` — which verifies
that the project's `OPTIONS` are what actually prevent the deadlock, not that raw `sqlite3` can
be made to behave.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.db import connections, transaction
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.db.utils import OperationalError

pytestmark = pytest.mark.integration

THREADS = 4
ITERATIONS = 25

#: A second database alias, registered per-test, pointing at a real file in tmp_path.
ALIAS = "concurrency_probe"


def _project_sqlite_options() -> dict[str, Any]:
    """The OPTIONS the project configures for SQLite — the subject under test."""
    return dict(settings.DATABASES["default"].get("OPTIONS", {}))


def _file_backed_connection(path: Path) -> DatabaseWrapper:
    """A Django SQLite connection to a real file, using the project's own OPTIONS."""
    return DatabaseWrapper(
        {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(path),
            "OPTIONS": _project_sqlite_options(),
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
            "ATOMIC_REQUESTS": False,
            "AUTOCOMMIT": True,
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False,
            "TIME_ZONE": None,
            "TEST": {"NAME": None, "MIRROR": None, "CHARSET": None, "COLLATION": None, "MIGRATE": True},
        },
        alias="concurrency-probe",
    )


@pytest.fixture(autouse=True)
def _allow_our_own_database(django_db_blocker: Any) -> Any:
    """Let this module open its own connection.

    pytest-django blocks database access globally, including to a database it did not create.
    These tests deliberately use a temp **file** rather than the suite's in-memory test DB —
    that is the whole point, since file locking is what is being exercised — so the block has to
    be lifted explicitly. Nothing here touches the test database.
    """
    with django_db_blocker.unblock():
        yield


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    """A real SQLite file seeded with one row to contend over."""
    path = tmp_path / "contention.sqlite3"
    conn = _file_backed_connection(path)
    with conn.cursor() as cursor:
        cursor.execute("CREATE TABLE counter (id INTEGER PRIMARY KEY, n INTEGER)")
        cursor.execute("INSERT INTO counter (id, n) VALUES (1, 0)")
    conn.close()
    return path


@pytest.fixture
def probe_alias(db_file: Path) -> Any:
    """Register the temp file as a real Django database alias, then tear it down.

    Registering it is what lets the tests use ``transaction.atomic(using=...)`` — the same call
    the application makes, and the **only** path that emits ``BEGIN IMMEDIATE``. Driving the
    connection any other way (raw ``BEGIN``, or ``set_autocommit(False)`` on its own) silently
    skips the setting, which makes a test that looks right pass whether or not the fix is there.
    """
    settings.DATABASES[ALIAS] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(db_file),
        "OPTIONS": _project_sqlite_options(),
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
        "TEST": {"NAME": None, "MIRROR": None, "CHARSET": None, "COLLATION": None, "MIGRATE": True},
    }
    try:
        yield ALIAS
    finally:
        connections.close_all()
        settings.DATABASES.pop(ALIAS, None)


# --- The configuration that makes it true (asserted against the real settings) -------------


def test_sqlite_starts_transactions_immediately() -> None:
    """`transaction_mode=IMMEDIATE` is the setting that actually prevents the deadlock."""
    assert _project_sqlite_options().get("transaction_mode") == "IMMEDIATE", (
        "without IMMEDIATE a read-then-write transaction upgrade fails instantly with "
        "'database is locked', and busy_timeout does not help"
    )


def test_sqlite_enables_wal_so_readers_do_not_block_behind_a_writer() -> None:
    assert "journal_mode=WAL" in _project_sqlite_options().get("init_command", "")


def test_sqlite_has_an_explicit_busy_timeout() -> None:
    """Explicit rather than inherited: under IMMEDIATE this is what contenders queue on."""
    assert _project_sqlite_options().get("timeout", 0) >= 5


def test_the_options_are_applied_to_a_real_file(db_file: Path) -> None:
    """Settings can say anything; this checks the pragmas SQLite actually ends up with."""
    conn = _file_backed_connection(db_file)
    try:
        with conn.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode")
            assert cursor.fetchone()[0].lower() == "wal"
            cursor.execute("PRAGMA busy_timeout")
            assert cursor.fetchone()[0] >= 5000
        assert conn.transaction_mode == "IMMEDIATE"
    finally:
        conn.close()


# --- The behaviour it buys -----------------------------------------------------------------


def test_concurrent_read_then_write_transactions_do_not_deadlock(probe_alias: str) -> None:
    """Four threads doing what the web process and the worker do between them.

    Threads rather than processes because Django opens one connection per thread, so the
    file-level lock contention is identical — and it stays runnable on Windows, which is the
    platform with no fallback.
    """
    errors: list[str] = []

    def churn() -> None:
        try:
            for _ in range(ITERATIONS):
                # transaction.atomic() is the application's path, and the one that emits
                # BEGIN IMMEDIATE. Anything else skips the setting entirely.
                with transaction.atomic(using=probe_alias):
                    with connections[probe_alias].cursor() as cursor:
                        cursor.execute("SELECT n FROM counter WHERE id = 1")  # read...
                        cursor.fetchone()
                        # Widen the read->write window: without it the transactions rarely
                        # overlap on a fast machine and the test passes with the fix removed,
                        # i.e. it would be decorative. Ablation-verified both ways.
                        time.sleep(0.002)
                        cursor.execute("UPDATE counter SET n = n + 1 WHERE id = 1")  # ...write
        except OperationalError as exc:  # pragma: no cover - the message is the point
            errors.append(str(exc))
        finally:
            connections[probe_alias].close()

    threads = [threading.Thread(target=churn) for _ in range(THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, f"concurrent writers hit SQLite contention: {errors}"


def test_every_concurrent_write_landed(probe_alias: str, db_file: Path) -> None:
    """No lost updates either — silently dropping writes would be a worse outcome than an error."""

    def churn() -> None:
        try:
            for _ in range(ITERATIONS):
                with transaction.atomic(using=probe_alias), connections[probe_alias].cursor() as cursor:
                    cursor.execute("UPDATE counter SET n = n + 1 WHERE id = 1")
        finally:
            connections[probe_alias].close()

    threads = [threading.Thread(target=churn) for _ in range(THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    conn = _file_backed_connection(db_file)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT n FROM counter WHERE id = 1")
            assert cursor.fetchone()[0] == THREADS * ITERATIONS
    finally:
        conn.close()


def test_a_reader_is_not_blocked_by_an_open_writer(db_file: Path) -> None:
    """What WAL buys, separately from the deadlock fix.

    Under the default rollback journal a reader waits behind an uncommitted writer; under WAL it
    reads the last committed snapshot immediately. `pixi run dev` serves pages while the worker
    writes phase progress, so this is the everyday case rather than an edge one.
    """
    writer_ready = threading.Event()
    reader_done = threading.Event()
    failures: list[str] = []

    def hold_a_write_open() -> None:
        conn = _file_backed_connection(db_file)
        try:
            conn.set_autocommit(False)
            with conn.cursor() as cursor:
                cursor.execute("UPDATE counter SET n = n + 1 WHERE id = 1")
                writer_ready.set()
                reader_done.wait(timeout=15)
            conn.commit()
            conn.set_autocommit(True)
        finally:
            conn.close()

    writer = threading.Thread(target=hold_a_write_open)
    writer.start()
    try:
        assert writer_ready.wait(timeout=15)
        reader = _file_backed_connection(db_file)
        try:
            with reader.cursor() as cursor:
                cursor.execute("SELECT n FROM counter WHERE id = 1")
                assert cursor.fetchone() is not None
        except OperationalError as exc:  # pragma: no cover
            failures.append(str(exc))
        finally:
            reader.close()
    finally:
        reader_done.set()
        writer.join(timeout=15)

    assert not failures, f"a reader blocked behind an open writer: {failures}"
