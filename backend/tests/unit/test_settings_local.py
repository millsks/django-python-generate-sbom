"""Story 20.3: the local dev settings module must be containerless.

Asserts the local settings resolve to SQLite + FileSystemStorage with no Postgres
or S3/object-storage backend, so the whole stack runs on macOS or Windows with no
Postgres, Redis, MinIO, or Docker. Pure settings introspection — no network or DB.
"""

from config.settings import local


def test_local_database_is_sqlite() -> None:
    assert local.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"


def test_local_database_is_not_postgres() -> None:
    assert "postgres" not in local.DATABASES["default"]["ENGINE"].lower()


def test_local_default_storage_is_filesystem() -> None:
    assert local.STORAGES["default"]["BACKEND"] == "django.core.files.storage.FileSystemStorage"


def test_local_has_no_s3_storage_backend() -> None:
    for cfg in local.STORAGES.values():
        assert "s3" not in cfg["BACKEND"].lower()
