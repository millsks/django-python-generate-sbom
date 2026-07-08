"""Story 20.4: cross-platform, containerless Celery transport.

Pure settings introspection (no broker, DB, or network). Asserts that:

* the containerless local settings select a Kombu filesystem:// broker + a django-db
  result backend (so local dev needs no Redis);
* the broker/beat paths are repo-relative and OS-portable (no POSIX-only ``/tmp``);
* the test settings force Celery eager mode so the unit suite runs offline;
* the container/prod base settings still use Redis (the prod path is untouched).
"""

from pathlib import Path

from config.settings import base, local, test


def test_local_broker_is_filesystem() -> None:
    assert local.CELERY_BROKER_URL == "filesystem://"


def test_local_broker_is_not_redis() -> None:
    assert "redis" not in local.CELERY_BROKER_URL.lower()


def test_local_result_backend_is_django_db() -> None:
    assert local.CELERY_RESULT_BACKEND == "django-db"


def test_local_result_backend_is_not_redis() -> None:
    assert "redis" not in local.CELERY_RESULT_BACKEND.lower()


def test_local_broker_transport_options_point_at_repo_local_dirs() -> None:
    opts = local.CELERY_BROKER_TRANSPORT_OPTIONS
    celery_dir = str(local.CELERY_DIR)
    for key in ("data_folder_in", "data_folder_out", "processed_folder"):
        assert opts[key].startswith(celery_dir)


def test_local_broker_dirs_are_created_on_import() -> None:
    opts = local.CELERY_BROKER_TRANSPORT_OPTIONS
    for key in ("data_folder_in", "data_folder_out", "processed_folder"):
        assert Path(opts[key]).is_dir()


def test_local_celery_dir_is_under_backend_base() -> None:
    # BASE_DIR is the backend/ directory; the broker tree lives under it so the path is
    # repo-relative and OS-correct on Windows (no hardcoded /tmp).
    assert local.CELERY_DIR == local.BASE_DIR / ".celery"


def test_test_settings_run_celery_eagerly() -> None:
    assert test.CELERY_TASK_ALWAYS_EAGER is True


def test_test_settings_propagate_eager_task_errors() -> None:
    assert test.CELERY_TASK_EAGER_PROPAGATES is True


def test_django_celery_results_app_installed() -> None:
    assert "django_celery_results" in base.INSTALLED_APPS


def test_base_broker_still_uses_redis() -> None:
    # The container/prod path is byte-identical: base keeps the Redis broker/backend.
    assert base.CELERY_BROKER_URL == base.REDIS_URL
    assert base.CELERY_RESULT_BACKEND == base.REDIS_URL
    assert base.REDIS_URL.startswith("redis://")
