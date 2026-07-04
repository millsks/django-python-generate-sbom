"""Celery SBOM pipeline task (pipeline queue, AD-4).

Story 3.2 dispatches this via ``delay_on_commit()`` (AD-10). The 8-phase body
(detect → resolve → generate → analysis group → persist) is implemented in
Story 3.5; here it is a registered stub so submission integrates end-to-end.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import structlog
from celery import shared_task

from generate_sbom.sbom.selectors import get_job_by_task_id
from generate_sbom.sbom.services import resolve_job_packages

logger = structlog.get_logger()


@shared_task(queue="pipeline")  # type: ignore[untyped-decorator]
def run_sbom_pipeline(task_id: str) -> None:
    """Run the SBOM generation pipeline for ``task_id`` (chain assembled in Story 3.5)."""
    logger.info("sbom_pipeline_dispatched", task_id=task_id)


@shared_task(bind=True, queue="pipeline")  # type: ignore[untyped-decorator]
def detect_and_parse_manifest(self: Any, task_id: str) -> dict[str, Any]:
    """Phase 1 (0-15%): confirm the job's manifest and detected format."""
    self.update_state(state="PROGRESS", meta={"progress": 5, "current_step": "detect & parse manifest"})
    job = get_job_by_task_id(task_id)
    logger.info(
        "phase_detect_parse",
        task_id=str(task_id),
        org_id=job.org_id,
        detected_format=job.manifest.detected_format,
    )
    return {"task_id": str(task_id), "detected_format": job.manifest.detected_format}


@shared_task(bind=True, queue="pipeline")  # type: ignore[untyped-decorator]
def resolve_transitive_deps(self: Any, prev: dict[str, Any]) -> dict[str, Any]:
    """Phase 2 (15-40%): resolve the full transitive package list."""
    task_id = prev["task_id"]
    self.update_state(state="PROGRESS", meta={"progress": 20, "current_step": "resolve dependencies"})
    packages = resolve_job_packages(task_id)
    logger.info("phase_resolve", task_id=str(task_id), package_count=len(packages))
    return {"task_id": task_id, "packages": [asdict(pkg) for pkg in packages]}
