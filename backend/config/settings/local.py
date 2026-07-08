# Containerless local-development settings (Story 20.3).
#
# This is the single DJANGO_SETTINGS_MODULE for containerless local dev. It inherits the
# SQLite (base DATABASES default) + FileSystemStorage (base STORAGES default) + console-log
# defaults, so the whole stack runs on macOS or Windows with no Postgres, Redis, MinIO, or
# Docker. Do NOT add a DATABASES/STORAGES swap here — the base defaults ARE the containerless
# defaults. manage.py, config.celery_app, and pytest all default to this module; wsgi.py and
# asgi.py default to config.settings.production and belong to the container/prod path only.
from config.settings.base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Human-friendly console logs in local dev (base configured JSON).
configure_structlog(json_logs=False)

# --- Containerless Celery transport (Story 20.4) ---
# A real, separate Celery worker drains SBOM jobs locally with no Redis and no container,
# on both macOS and Windows, by swapping only the transport + result backend (the Celery
# app and task graph are unchanged). The container/prod path keeps the Redis broker and
# result backend from base.py — nothing here touches base's REDIS_URL wiring.
#
# Broker: Kombu's `filesystem://` transport exchanges messages through a repo-local, OS-correct
# directory under a git-ignored `backend/.celery/broker/` tree (built with pathlib so the paths
# are correct on Windows, which has no `/tmp`). The folders are created on import so a fresh
# checkout can start a worker without a manual mkdir. NOTE: the transport writes messages to
# `data_folder_out` and reads them from `data_folder_in`, so both MUST be the SAME directory for
# a producer and a consumer to exchange messages; `processed_folder` holds consumed messages.
CELERY_DIR = BASE_DIR / ".celery"
_CELERY_BROKER_DIR = CELERY_DIR / "broker"
_CELERY_BROKER_MESSAGES = _CELERY_BROKER_DIR / "messages"
_CELERY_BROKER_PROCESSED = _CELERY_BROKER_DIR / "processed"
# The transport stores its exchange→queue table under `control_folder` (default: a `control/`
# dir in the CWD); pin it under .celery/ so nothing is written outside the git-ignored tree.
_CELERY_BROKER_CONTROL = _CELERY_BROKER_DIR / "control"
for _folder in (_CELERY_BROKER_MESSAGES, _CELERY_BROKER_PROCESSED, _CELERY_BROKER_CONTROL):
    _folder.mkdir(parents=True, exist_ok=True)

CELERY_BROKER_URL = "filesystem://"
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "data_folder_in": str(_CELERY_BROKER_MESSAGES),
    "data_folder_out": str(_CELERY_BROKER_MESSAGES),
    "processed_folder": str(_CELERY_BROKER_PROCESSED),
    "control_folder": str(_CELERY_BROKER_CONTROL),
    "store_processed": True,
}

# Result backend: django-celery-results' `django-db` persists results in the local SQLite DB
# (django_celery_results is in INSTALLED_APPS in base.py; its migrations create the tables),
# so results survive without Redis.
CELERY_RESULT_BACKEND = "django-db"
