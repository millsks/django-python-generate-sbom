"""Celery SBOM pipeline: the orchestrated eight-phase chain (Stories 3.5, 4.6).

Canvas (solution-design.md §4.1): ``detect → resolve → generate → chord(group of
the four real analysis tasks, aggregate) → persist``. The analysis tasks live in
``tasks/analysis.py`` and run on the ``analysis`` queue; Phases 1-3, aggregate, and
8 run on ``pipeline`` (AD-4).

``task_id`` threads the whole chain — only keys/counts flow through the result
backend, never blobs (AD-6). All tasks are ``@shared_task`` — no Celery app import
(AD-10). Status is written only via ``sbom/services.py`` (AD-12).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from typing import Any

import structlog
from celery import chain, chord, group, shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from generate_sbom.analysis.services import license as license_service
from generate_sbom.analysis.services.reports import write_report
from generate_sbom.sbom import services
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.parsers import PackageSpec, ResolutionError
from generate_sbom.sbom.selectors import get_job_by_task_id
from generate_sbom.tasks.analysis import (
    build_dependency_graph,
    check_version_currency,
    classify_licenses,
    scan_vulnerabilities,
)

logger = structlog.get_logger()


def _report(task: Any, task_id: str, progress: int, step: str) -> None:
    """Report progress via Celery state and mirror it to the job (keeps polled progress monotonic)."""
    task.update_state(state="PROGRESS", meta={"progress": progress, "current_step": step})
    services.update_job_status(task_id, SBOMJob.Status.PROGRESS, progress=progress, current_step=step)


def _fail_if_unfinished(task_id: str, *, failure_reason: str) -> None:
    """Safety net: never leave a job stuck at PROGRESS when a phase raises.

    Marks the job FAILED unless a phase already reached a terminal state (whose
    reason we then preserve). Best-effort — a lookup failure must not mask the
    original phase error.
    """
    try:
        job = get_job_by_task_id(task_id)
    except SBOMJob.DoesNotExist:
        return
    if job.status in (SBOMJob.Status.SUCCESS, SBOMJob.Status.FAILED):
        return
    services.update_job_status(task_id, SBOMJob.Status.FAILED, failure_reason=failure_reason)


@contextmanager
def _phase_guard(task_id: str, *, detected_format: str = "") -> Iterator[None]:
    """Mark the job FAILED on any phase failure, and log it with its manifest format.

    On ``SoftTimeLimitExceeded`` the job is failed with reason ``soft_timeout`` and no
    partial SBOM is produced (FR-4.6). Any other failure is logged with the full
    traceback + manifest format (NFR-6.2) and finalizes the job as FAILED — preserving
    a specific reason a phase already set, else a generic ``pipeline_error`` — so a
    phase error can never leave the job stuck at PROGRESS.
    """
    try:
        yield
    except SoftTimeLimitExceeded:
        services.update_job_status(task_id, SBOMJob.Status.FAILED, failure_reason="soft_timeout")
        logger.error("phase_soft_timeout", task_id=str(task_id), detected_format=detected_format, exc_info=True)
        raise
    except Exception:
        logger.error("phase_failed", task_id=str(task_id), detected_format=detected_format, exc_info=True)
        _fail_if_unfinished(task_id, failure_reason="pipeline_error")
        raise


# --- Chain assembly ------------------------------------------------------------------


def build_pipeline(task_id: str) -> chain:
    """Assemble the eight-phase canvas for ``task_id`` (real analysis group, Story 4.6)."""
    analysis_group = group(
        scan_vulnerabilities.s(),
        classify_licenses.s(),
        build_dependency_graph.s(),
        check_version_currency.s(),
    )
    return chain(
        detect_and_parse_manifest.si(task_id),
        resolve_transitive_deps.s(),
        generate_sbom_document.s(),
        chord(analysis_group, aggregate_analysis_results.s(task_id)),
        persist_artifacts.si(task_id),
    )


@shared_task(queue="pipeline")  # type: ignore[untyped-decorator]
def run_sbom_pipeline(task_id: str) -> None:
    """Dispatch target (Story 3.2): assemble and launch the pipeline chain."""
    logger.info("sbom_pipeline_dispatched", task_id=task_id)
    build_pipeline(task_id).delay()


# --- Sequential phases (pipeline queue) ----------------------------------------------


@shared_task(bind=True, queue="pipeline")  # type: ignore[untyped-decorator]
def detect_and_parse_manifest(self: Any, task_id: str) -> dict[str, Any]:
    """Phase 1 (0-15%): confirm the job's manifest and detected format."""
    with _phase_guard(task_id):
        _report(self, task_id, 5, "detect & parse manifest")
        job = get_job_by_task_id(task_id)
        logger.info(
            "phase_detect_parse", task_id=str(task_id), org_id=job.org_id, detected_format=job.manifest.detected_format
        )
        return {"task_id": str(task_id), "detected_format": job.manifest.detected_format}


@shared_task(bind=True, queue="pipeline")  # type: ignore[untyped-decorator]
def resolve_transitive_deps(self: Any, prev: dict[str, Any]) -> dict[str, Any]:
    """Phase 2 (15-40%): resolve the full transitive package list."""
    task_id = prev["task_id"]
    with _phase_guard(task_id, detected_format=prev.get("detected_format", "")):
        _report(self, task_id, 20, "resolve dependencies")
        try:
            packages = services.resolve_job_packages(task_id)
        except ResolutionError:
            # A bad/unsatisfiable manifest is a hard-fail for the job (not a crash) —
            # give it a specific reason so the UI explains why instead of spinning.
            services.update_job_status(task_id, SBOMJob.Status.FAILED, failure_reason="resolution_failed")
            raise
        logger.info("phase_resolve", task_id=str(task_id), package_count=len(packages))
        return {"task_id": task_id, "packages": [asdict(pkg) for pkg in packages]}


@shared_task(bind=True, queue="pipeline")  # type: ignore[untyped-decorator]
def generate_sbom_document(self: Any, prev: dict[str, Any]) -> dict[str, Any]:
    """Phase 3 (40-55%): serialize the SBOM and write the blob to its final key.

    Hard-fail boundary (FR-4.5): a serializer error fails the whole job, no partial
    SBOM. The key + package count are recorded on the job; only the key threads
    onward (AD-6). Phase 8 finalizes the record.
    """
    task_id = prev["task_id"]
    job = get_job_by_task_id(task_id)
    with _phase_guard(task_id, detected_format=job.manifest.detected_format):
        _report(self, task_id, 45, "generate SBOM document")
        packages = [PackageSpec(**spec) for spec in prev["packages"]]
        provenance = services.build_provenance(job.manifest)
        # Resolve each package's license here (I/O), then hand it to the pure serializer (Story 8.25).
        # Same normalization Phase 5 uses, over the cached PyPI session — no doubled external load.
        license_map = license_service.build_license_map(packages)
        try:
            content, media_type = services.generate_sbom_document(packages, job.output_format, provenance, license_map)
        except services.SBOMGenerationError:
            services.update_job_status(task_id, SBOMJob.Status.FAILED, failure_reason="sbom_generation_failed")
            raise

        result_key = f"sbom-results/{job.org_id}/{task_id}/sbom.{services.sbom_extension(job.output_format)}"
        if default_storage.exists(result_key):
            default_storage.delete(result_key)
        default_storage.save(result_key, ContentFile(content))
        services.record_generation(task_id, result_key, len(packages))
        logger.info(
            "phase_generate",
            task_id=str(task_id),
            output_format=job.output_format,
            result_key=result_key,
            package_count=len(packages),
        )
        return {"task_id": task_id, "result_key": result_key, "package_count": len(packages), "media_type": media_type}


@shared_task(queue="pipeline")  # type: ignore[untyped-decorator]
def aggregate_analysis_results(results: list[dict[str, Any]], task_id: str) -> dict[str, Any]:
    """Chord callback (pipeline queue): persist the four analysis reports, then proceed to persist.

    Writes/updates one ``AnalysisReport`` per envelope (failed reports included, with
    their reason). Analysis-task failures never abort the chord — each task always
    returns an envelope (FR-4.5).
    """
    services.update_job_status(task_id, SBOMJob.Status.PROGRESS, progress=95, current_step="aggregate analysis")
    job = get_job_by_task_id(task_id)
    for envelope in results:
        write_report(job, envelope)
    services.record_analysis_summaries(task_id, results)
    failed = [envelope["report_type"] for envelope in results if envelope.get("failed")]
    logger.info("phase_aggregate", task_id=str(task_id), report_count=len(results), failed=failed)
    return {"task_id": task_id, "analysis": results}


@shared_task(bind=True, queue="pipeline")  # type: ignore[untyped-decorator]
def persist_artifacts(self: Any, task_id: str) -> dict[str, Any]:
    """Phase 8 (97-100%): finalize the job record — key, expiry, stats, SUCCESS (AD-6/12)."""
    with _phase_guard(task_id):
        _report(self, task_id, 97, "persist artifacts")
        job = get_job_by_task_id(task_id)
        if job.result_key is None:  # Phase 3 always records it; guard the invariant.
            services.update_job_status(task_id, SBOMJob.Status.FAILED, failure_reason="missing_artifact")
            raise ValueError(f"No artifact recorded for job {task_id}")
        services.finalize_job(task_id, job.result_key, job.summary_stats)
        logger.info("phase_persist", task_id=str(task_id), result_key=job.result_key)
        return {"task_id": task_id, "result_key": job.result_key}
