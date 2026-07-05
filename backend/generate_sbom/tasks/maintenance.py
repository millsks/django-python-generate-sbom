"""Scheduled maintenance tasks (queue set per task).

``@shared_task`` only — no Celery app import (AD-10). Scheduled via the beat
schedule in ``config/celery_app.py``.
"""

from __future__ import annotations

import structlog
from celery import shared_task

from generate_sbom.analysis.services import parselmouth
from generate_sbom.sbom import services as sbom_services

logger = structlog.get_logger()


@shared_task(queue="analysis")  # type: ignore[untyped-decorator]
def refresh_parselmouth_mapping() -> int:
    """Refresh the locally-stored conda↔PyPI name mapping from parselmouth (Story 8.10)."""
    count = parselmouth.refresh_mapping()
    logger.info("parselmouth_mapping_refreshed", entries=count)
    return count


@shared_task(queue="pipeline")  # type: ignore[untyped-decorator]
def purge_expired_artifacts() -> int:
    """Purge artifacts for jobs past their retention expiry (Story 7.1); daily via Beat.

    Delegates to the reusable service sweep and returns the number of jobs cleaned.
    """
    count = sbom_services.purge_expired_artifacts()
    logger.info("expired_artifacts_purged", jobs_cleaned=count)
    return count
