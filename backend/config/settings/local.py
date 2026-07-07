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
# The container-free Celery config (a Kombu filesystem:// broker + a django-celery-results
# SQLite result backend, with a real cross-platform worker) is configured here by Story 20.4.
# Until then the base Redis defaults (CELERY_BROKER_URL / CELERY_RESULT_BACKEND) still apply.
