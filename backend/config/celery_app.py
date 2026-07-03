# Celery application for the django-python-generate-sbom project.
#
# Two queues (AD-4): `pipeline` (phases 1-3, 8, plus Beat cleanup) and `analysis`
# (phases 4-7). Task modules use @shared_task only (no Celery app import). Views
# dispatch with delay_on_commit() (AD-10). Per-task routes are added by the
# epics that define the tasks; the queue names, default queue, and time limits
# are supplied via CELERY_* Django settings (read lazily through the CELERY
# namespace) so this module touches no settings at import time.
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("generate_sbom")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Beat schedule placeholder; the nightly artifact-cleanup task is added in Epic 7.
app.conf.beat_schedule = {}
