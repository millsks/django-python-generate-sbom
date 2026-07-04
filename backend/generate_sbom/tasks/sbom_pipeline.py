"""Celery SBOM pipeline task (pipeline queue, AD-4).

Story 3.2 dispatches this via ``delay_on_commit()`` (AD-10). The 8-phase body
(detect → resolve → generate → analysis group → persist) is implemented in
Story 3.5; here it is a registered stub so submission integrates end-to-end.
"""

from __future__ import annotations

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(queue="pipeline")  # type: ignore[untyped-decorator]
def run_sbom_pipeline(task_id: str) -> None:
    """Run the SBOM generation pipeline for ``task_id`` (stub — Story 3.5)."""
    logger.info("sbom_pipeline_dispatched", task_id=task_id)
