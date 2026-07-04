"""Celery SBOM pipeline: the orchestrated eight-phase chain (Story 3.5).

Canvas (solution-design.md §4.1): ``detect → resolve → generate → chord(group of
four analysis tasks, aggregate) → persist``. The analysis group is stubbed here
(no-op envelopes); Epic 4 replaces the four bodies without changing the shape.

``task_id`` threads the whole chain — only keys/counts flow through the result
backend, never blobs (AD-6). Phases 1-3, aggregate, and 8 run on the ``pipeline``
queue; the analysis group runs on ``analysis`` (AD-4). All tasks are
``@shared_task`` — no Celery app import (AD-10). Status is written only via
``sbom/services.py`` (AD-12).
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

from generate_sbom.sbom import services
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.parsers import PackageSpec
from generate_sbom.sbom.selectors import get_job_by_task_id

logger = structlog.get_logger()


def _report(task: Any, task_id: str, progress: int, step: str, *, mirror: bool) -> None:
    """Report progress via Celery state, and (for sequential phases) mirror it to the job.

    Only sequential phases mirror to ``SBOMJob`` so the polled DB progress stays
    monotonic; the parallel analysis stubs report Celery state only (``mirror=False``).
    """
    task.update_state(state="PROGRESS", meta={"progress": progress, "current_step": step})
    if mirror:
        services.update_job_status(task_id, SBOMJob.Status.PROGRESS, progress=progress, current_step=step)


@contextmanager
def _phase_guard(task_id: str, *, detected_format: str = "") -> Iterator[None]:
    """Mark the job FAILED on a soft timeout, and log any failure with its manifest format.

    On ``SoftTimeLimitExceeded`` the job is failed with reason ``soft_timeout`` and no
    partial SBOM is produced (FR-4.6). Other failures are logged with the full
    traceback + manifest format (NFR-6.2), leaving any reason a phase already set intact.
    """
    try:
        yield
    except SoftTimeLimitExceeded:
        services.update_job_status(task_id, SBOMJob.Status.FAILED, failure_reason="soft_timeout")
        logger.error("phase_soft_timeout", task_id=str(task_id), detected_format=detected_format, exc_info=True)
        raise
    except Exception:
        logger.error("phase_failed", task_id=str(task_id), detected_format=detected_format, exc_info=True)
        raise


# --- Chain assembly ------------------------------------------------------------------


def build_pipeline(task_id: str) -> chain:
    """Assemble the eight-phase canvas for ``task_id`` (analysis group stubbed, AC #1/#2)."""
    analysis_group = group(
        scan_vulnerabilities.s(),
        analyze_licenses.s(),
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
        _report(self, task_id, 5, "detect & parse manifest", mirror=True)
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
        _report(self, task_id, 20, "resolve dependencies", mirror=True)
        packages = services.resolve_job_packages(task_id)
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
        _report(self, task_id, 45, "generate SBOM document", mirror=True)
        packages = [PackageSpec(**spec) for spec in prev["packages"]]
        provenance = services.build_provenance(job.manifest)
        try:
            content, media_type = services.generate_sbom_document(packages, job.output_format, provenance)
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
    """Chord callback (pipeline queue): collect analysis envelopes and proceed to persist.

    Epic 4 merges the report summaries into ``summary_stats`` here; the stub just
    records that the analysis block completed. Analysis-task failures never abort
    the chord — each task always returns an envelope.
    """
    services.update_job_status(task_id, SBOMJob.Status.PROGRESS, progress=95, current_step="aggregate analysis")
    failed = [r["report_type"] for r in results if r.get("failed")]
    logger.info("phase_aggregate", task_id=str(task_id), report_count=len(results), failed=failed)
    return {"task_id": task_id, "analysis": results}


@shared_task(bind=True, queue="pipeline")  # type: ignore[untyped-decorator]
def persist_artifacts(self: Any, task_id: str) -> dict[str, Any]:
    """Phase 8 (97-100%): finalize the job record — key, expiry, stats, SUCCESS (AD-6/12)."""
    with _phase_guard(task_id):
        _report(self, task_id, 97, "persist artifacts", mirror=True)
        job = get_job_by_task_id(task_id)
        if job.result_key is None:  # Phase 3 always records it; guard the invariant.
            services.update_job_status(task_id, SBOMJob.Status.FAILED, failure_reason="missing_artifact")
            raise ValueError(f"No artifact recorded for job {task_id}")
        services.finalize_job(task_id, job.result_key, job.summary_stats)
        logger.info("phase_persist", task_id=str(task_id), result_key=job.result_key)
        return {"task_id": task_id, "result_key": job.result_key}


# --- Analysis group (analysis queue) — STUBS; Epic 4 replaces the bodies -------------

_EMPTY_SUMMARY: dict[str, Any] = {}


def _stub_envelope(report_type: str) -> dict[str, Any]:
    """The standard analysis envelope with empty/false values (spine contract, AC #2)."""
    return {
        "report_type": report_type,
        "artifact_key": None,
        "summary": _EMPTY_SUMMARY,
        "failed": False,
        "failure_reason": None,
    }


@shared_task(bind=True, queue="analysis")  # type: ignore[untyped-decorator]
def scan_vulnerabilities(self: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """Phase 4 (55-80%) stub — Epic 4 scans the resolved packages for CVEs."""
    _report(self, ctx["task_id"], 55, "vulnerability scan", mirror=False)
    return _stub_envelope("vulnerability")


@shared_task(bind=True, queue="analysis")  # type: ignore[untyped-decorator]
def analyze_licenses(self: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """Phase 5 (80-88%) stub — Epic 4 resolves license obligations."""
    _report(self, ctx["task_id"], 80, "license analysis", mirror=False)
    return _stub_envelope("license")


@shared_task(bind=True, queue="analysis")  # type: ignore[untyped-decorator]
def build_dependency_graph(self: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """Phase 6 (88-93%) stub — Epic 4 builds the dependency graph."""
    _report(self, ctx["task_id"], 88, "dependency graph", mirror=False)
    return _stub_envelope("dependency_graph")


@shared_task(bind=True, queue="analysis")  # type: ignore[untyped-decorator]
def check_version_currency(self: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """Phase 7 (93-97%) stub — Epic 4 checks how current each dependency is."""
    _report(self, ctx["task_id"], 93, "version currency", mirror=False)
    return _stub_envelope("version_currency")
