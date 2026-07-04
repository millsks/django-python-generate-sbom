"""Celery SBOM pipeline tasks (pipeline queue, AD-4).

Story 3.2 dispatches ``run_sbom_pipeline`` via ``delay_on_commit()`` (AD-10).
The phase bodies are built up across Stories 3.3-3.5; the chain is assembled in
Story 3.5. Phases here all route to the ``pipeline`` queue; only analysis
(Phases 4-7, Epic 4) uses the ``analysis`` queue.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import structlog
from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from generate_sbom.sbom import services
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.parsers import PackageSpec
from generate_sbom.sbom.selectors import get_job_by_task_id

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
    packages = services.resolve_job_packages(task_id)
    logger.info("phase_resolve", task_id=str(task_id), package_count=len(packages))
    return {"task_id": task_id, "packages": [asdict(pkg) for pkg in packages]}


@shared_task(bind=True, queue="pipeline")  # type: ignore[untyped-decorator]
def generate_sbom_document(self: Any, prev: dict[str, Any]) -> dict[str, Any]:
    """Phase 3 (40-55%): serialize the SBOM and write the blob to its final key.

    Phase 3 is the hard-fail boundary (FR-4.5): a serializer error fails the whole
    job with no partial SBOM. Only the artifact key flows onward — the blob never
    transits Redis (AD-6); Phase 8 finalizes the DB record.
    """
    task_id = prev["task_id"]
    self.update_state(state="PROGRESS", meta={"progress": 45, "current_step": "generate SBOM document"})
    packages = [PackageSpec(**spec) for spec in prev["packages"]]
    job = get_job_by_task_id(task_id)
    provenance = services.build_provenance(job.manifest)
    try:
        content, media_type = services.generate_sbom_document(packages, job.output_format, provenance)
    except services.SBOMGenerationError as exc:
        services.update_job_status(task_id, SBOMJob.Status.FAILED, failure_reason="sbom_generation_failed")
        logger.error(
            "phase_generate_failed",
            task_id=str(task_id),
            output_format=job.output_format,
            error=str(exc),
            exc_info=True,
        )
        raise

    result_key = f"sbom-results/{job.org_id}/{task_id}/sbom.{services.sbom_extension(job.output_format)}"
    if default_storage.exists(result_key):
        default_storage.delete(result_key)
    default_storage.save(result_key, ContentFile(content))
    self.update_state(state="PROGRESS", meta={"progress": 55, "current_step": "SBOM document generated"})
    logger.info(
        "phase_generate",
        task_id=str(task_id),
        output_format=job.output_format,
        result_key=result_key,
        package_count=len(packages),
    )
    return {"task_id": task_id, "result_key": result_key, "package_count": len(packages), "media_type": media_type}


@shared_task(bind=True, queue="pipeline")  # type: ignore[untyped-decorator]
def persist_artifacts(self: Any, prev: dict[str, Any]) -> dict[str, Any]:
    """Phase 8 (97-100%): finalize the job record — key, expiry, stats, SUCCESS (AD-6/12)."""
    task_id = prev["task_id"]
    self.update_state(state="PROGRESS", meta={"progress": 97, "current_step": "persist artifacts"})
    summary_stats: dict[str, object] = {"total_packages": prev["package_count"]}
    services.finalize_job(task_id, prev["result_key"], summary_stats)
    self.update_state(state="PROGRESS", meta={"progress": 100, "current_step": "complete"})
    logger.info(
        "phase_persist",
        task_id=str(task_id),
        result_key=prev["result_key"],
        total_packages=prev["package_count"],
    )
    return {"task_id": task_id, "result_key": prev["result_key"]}
