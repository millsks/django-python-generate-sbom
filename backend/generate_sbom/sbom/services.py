"""Mutation services for the sbom app (AD-3).

``SBOMJob.status`` is written ONLY here (AD-12): task code calls
``update_job_status`` / ``finalize_job``; the generate view sets the initial
PENDING via ``create_job``. DRF views never write status otherwise.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import cast

import structlog
from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import QuerySet
from django.utils import timezone

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.users.models import Org, User

from .generation import (
    Provenance,
    SBOMGenerationError,
    generate_sbom_document,
    sbom_extension,
)
from .models import SBOMJob
from .parsers import PackageSpec, resolve_packages
from .selectors import get_job_by_task_id

__all__ = [
    "OUTPUT_FORMAT_MAP",
    "Provenance",
    "SBOMGenerationError",
    "build_provenance",
    "create_job",
    "delete_job_artifacts",
    "estimate_seconds",
    "finalize_job",
    "generate_sbom_document",
    "mark_stale_job_timed_out",
    "purge_expired_artifacts",
    "record_analysis_summaries",
    "record_generation",
    "resolve_job_packages",
    "sbom_extension",
    "update_job_status",
]

logger = structlog.get_logger()

# API-facing output_format → internal serializer id (solution-design §3.3).
OUTPUT_FORMAT_MAP = {
    "cdx-json": "cyclonedx-json",
    "cdx-xml": "cyclonedx-xml",
    "spdx-2.3": "spdx-json",
}
DEFAULT_OUTPUT_FORMAT = "cdx-json"


def create_job(org: Org, manifest: ManifestUpload, user: User | None, output_format: str) -> SBOMJob:
    """Create a PENDING job (the view's initial status write; AD-12)."""
    return SBOMJob.objects.create(
        org=org,
        manifest=manifest,
        user=user,
        output_format=output_format,
        status=SBOMJob.Status.PENDING,
    )


def update_job_status(
    task_id: str,
    status: str,
    *,
    progress: int = 0,
    current_step: str = "",
    failure_reason: str | None = None,
) -> None:
    """Update a job's status/progress. The sole status writer for task code (AD-12)."""
    SBOMJob.objects.filter(task_id=task_id).update(
        status=status, progress=progress, current_step=current_step, failure_reason=failure_reason
    )


def record_generation(task_id: str, result_key: str, package_count: int) -> None:
    """Store the generated artifact key + package count on the job (Phase 3, pre-SUCCESS).

    Not a status write: the blob is keyed here so Phase 8 finalizes by ``task_id``
    alone (only the key threads through the chain, never the blob — AD-6).
    """
    SBOMJob.objects.filter(task_id=task_id).update(
        result_key=result_key, summary_stats={"total_packages": package_count}
    )


def record_analysis_summaries(task_id: str, envelopes: list[dict[str, object]]) -> None:
    """Merge the analysis report summaries into ``summary_stats['reports']`` (Story 5.2).

    Lets the Overview tab read every count from ``summary_stats`` without a per-report
    fetch (NFR-2.2). Only the report counts + the failed flag are kept.
    """
    reports: dict[str, object] = {}
    for envelope in envelopes:
        raw = envelope.get("summary")
        summary = raw if isinstance(raw, dict) else {}
        reports[str(envelope["report_type"])] = {
            "failed": envelope["failed"],
            "failure_reason": envelope["failure_reason"],
            **summary,
        }
    job = get_job_by_task_id(task_id)
    stats = dict(job.summary_stats)
    stats["reports"] = reports
    SBOMJob.objects.filter(task_id=task_id).update(summary_stats=stats)


def mark_stale_job_timed_out(job: SBOMJob) -> bool:
    """Mark a still-running job FAILED (hard_timeout) if it outlived the hard limit (FR-4.6).

    A hard timeout force-kills the worker, so the task cannot mark itself; a status
    poll or cleanup sweep detects the stale PENDING/PROGRESS job instead.
    """
    if job.status not in (SBOMJob.Status.PENDING, SBOMJob.Status.PROGRESS):
        return False
    hard_limit = timedelta(seconds=settings.CELERY_TASK_TIME_LIMIT)
    if timezone.now() - job.created_at <= hard_limit:
        return False
    update_job_status(str(job.task_id), SBOMJob.Status.FAILED, failure_reason="hard_timeout")
    logger.warning("job_hard_timeout", task_id=str(job.task_id), org_id=job.org_id)
    return True


def finalize_job(task_id: str, result_key: str, summary_stats: dict[str, object]) -> None:
    """Mark a job SUCCESS with its artifact key and set the retention expiry (AD-12).

    The expiry window is ``settings.ARTIFACT_RETENTION_DAYS`` (default 30, env-overridable;
    Story 7.1), after which the daily cleanup purges the blobs.
    """
    now = timezone.now()
    SBOMJob.objects.filter(task_id=task_id).update(
        status=SBOMJob.Status.SUCCESS,
        progress=100,
        result_key=result_key,
        summary_stats=summary_stats,
        completed_at=now,
        artifacts_expire_at=now + timedelta(days=settings.ARTIFACT_RETENTION_DAYS),
    )


def delete_job_artifacts(job: SBOMJob) -> bool:
    """Delete a job's SBOM + analysis-report blobs from storage and null their keys.

    The ``SBOMJob`` and its ``AnalysisReport`` rows — with all metadata (status,
    package count, summary statistics) — are retained forever (FR-8.1); only the blobs
    and the key columns (``result_key`` / ``artifact_key``) are removed. Idempotent: a
    job whose artifacts were already cleaned (``result_key`` is null) is skipped and
    returns ``False``. Pure service-layer primitive (AD-3) reused by the scheduled
    cleanup task and by on-demand deletion (Story 7.2).
    """
    if not job.result_key:
        return False
    report_keys = [report.artifact_key for report in job.reports.all() if report.artifact_key]
    for key in (job.result_key, *report_keys):
        if default_storage.exists(key):
            default_storage.delete(key)
    job.reports.filter(artifact_key__isnull=False).update(artifact_key=None)
    SBOMJob.objects.filter(task_id=job.task_id).update(result_key=None)
    logger.info("job_artifacts_deleted", task_id=str(job.task_id), org_id=job.org_id, blobs=len(report_keys) + 1)
    return True


def delete_artifacts_for_jobs(jobs: Iterable[SBOMJob]) -> int:
    """Delete artifacts for each job via ``delete_job_artifacts``; return how many were purged.

    On-demand (Story 7.2) bulk primitive: reuses the single-job cleanup so there is no
    duplicated deletion logic (AD-3). Jobs already cleaned are skipped and not counted.
    """
    return sum(1 for job in jobs if delete_job_artifacts(job))


def purge_expired_artifacts(now: datetime | None = None) -> int:
    """Purge artifacts for every job past its ``artifacts_expire_at`` (the daily sweep).

    Selects expired jobs that still hold artifacts (``result_key__isnull=False``, AD-6),
    deletes each one's blobs via :func:`delete_job_artifacts`, and returns the number of
    jobs cleaned. Job metadata is never deleted (FR-8.1).
    """
    cutoff = now or timezone.now()
    expired = cast(
        "QuerySet[SBOMJob]",
        SBOMJob.objects.filter(artifacts_expire_at__lte=cutoff, result_key__isnull=False),
    )
    cleaned = 0
    for job in expired:
        if delete_job_artifacts(job):
            cleaned += 1
    return cleaned


def build_provenance(manifest: ManifestUpload) -> Provenance:
    """Lift the four provenance fields off a manifest for SBOM metadata (FR-3.8)."""
    return Provenance(
        application_id=manifest.application_id,
        component_name=manifest.component_name,
        repository_url=manifest.repository_url,
        source_branch=manifest.source_branch,
    )


def resolve_job_packages(task_id: str) -> list[PackageSpec]:
    """Load a job's manifest, download it, and resolve the full package list (Phase 2)."""
    job = get_job_by_task_id(task_id)
    with job.manifest.file.open("rb") as handle:
        content = handle.read()
    return resolve_packages(job.manifest.detected_format, content)


def estimate_seconds(detected_format: str, size_bytes: int) -> int:
    """Rough processing-time estimate from format + file size (FR-3.5)."""
    megabytes = size_bytes / (1024 * 1024)
    estimate = 15 + megabytes * 10
    if detected_format == ManifestUpload.Format.CONDA:
        estimate += 10  # conda solver overhead
    return int(estimate)
