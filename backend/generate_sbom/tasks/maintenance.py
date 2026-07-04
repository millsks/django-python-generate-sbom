"""Scheduled maintenance tasks (analysis queue).

``@shared_task`` only — no Celery app import (AD-10). Scheduled via the beat
schedule in ``config/celery_app.py``.
"""

from __future__ import annotations

import structlog
from celery import shared_task

from generate_sbom.analysis.services import parselmouth

logger = structlog.get_logger()


@shared_task(queue="analysis")  # type: ignore[untyped-decorator]
def refresh_parselmouth_mapping() -> int:
    """Refresh the locally-stored conda↔PyPI name mapping from parselmouth (Story 8.10)."""
    count = parselmouth.refresh_mapping()
    logger.info("parselmouth_mapping_refreshed", entries=count)
    return count
