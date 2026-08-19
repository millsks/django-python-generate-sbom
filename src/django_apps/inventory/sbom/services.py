"""Mutation services for the sbom app (AD-3).

``SBOMJob.status`` is written ONLY here (AD-12): task code calls
``update_job_status`` / ``finalize_job``; the generate view sets the initial
PENDING via ``create_job``. DRF views never write status otherwise.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any, cast

import structlog
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import QuerySet, Value
from django.db.models.functions import Greatest
from django.utils import timezone

from inventory.common.users import UserT, user_ref
from inventory.manifests.models import ManifestUpload
from inventory.manifests.services import upload_manifest
from inventory.users.models import Org

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
    "ACTIVE_STATUSES",
    "OUTPUT_FORMAT_CHOICES",
    "OUTPUT_FORMAT_MAP",
    "TERMINAL_STATUSES",
    "ConcurrencyLimitError",
    "Provenance",
    "SBOMGenerationError",
    "at_concurrency_limit",
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
    "submit_job",
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

# Human labels for the same keys. Kept beside the map on purpose: Story 6.4 was caused by the
# frontend and backend keeping *separate* format lists that drifted, and the fix is that there
# is exactly one canonical list. `test_output_format_choices_cover_every_supported_format`
# fails if a format is added to the map without a label here.
OUTPUT_FORMAT_LABELS = {
    "cdx-json": "CycloneDX (JSON)",
    "cdx-xml": "CycloneDX (XML)",
    "spdx-2.3": "SPDX (JSON)",
}

#: Choices for any form or serializer offering an output format. Derived from
#: OUTPUT_FORMAT_MAP so a form can never offer a value the backend would reject.
OUTPUT_FORMAT_CHOICES = tuple((value, OUTPUT_FORMAT_LABELS[value]) for value in OUTPUT_FORMAT_MAP)

#: Statuses that count against the per-org concurrency gate (AD-7).
ACTIVE_STATUSES = (SBOMJob.Status.PENDING, SBOMJob.Status.PROGRESS)

#: Statuses a job never leaves. Polling stops here (Story 21.11), mirroring the SPA's
#: TERMINAL_STATUSES in useJobStatus.ts. Defined once so the row trigger, the results gate,
#: and any later view agree on when work is finished.
TERMINAL_STATUSES = (SBOMJob.Status.SUCCESS, SBOMJob.Status.FAILED)


class ConcurrencyLimitError(Exception):
    """Raised when an org is already at ``SBOM_MAX_CONCURRENT_JOBS_PER_ORG`` (AD-7)."""

    #: Mirrors the ``Retry-After`` header the API returns with its 429.
    retry_after_seconds = 60
    message = (
        "This organization already has the maximum number of jobs running. "
        "Wait for one to finish and try again in about a minute."
    )

    def __init__(self) -> None:
        """Initialise with the shared user-facing message."""
        super().__init__(self.message)


def at_concurrency_limit(org: Org) -> bool:
    """Return True if ``org`` is at or above its concurrent-job limit (AD-7).

    The single implementation of the gate. Both the DRF endpoint and the server-rendered
    upload page call it, so the API and the web UI cannot diverge on the limit.
    """
    jobs = cast("QuerySet[SBOMJob]", SBOMJob.objects.for_org(org))
    active = jobs.filter(status__in=ACTIVE_STATUSES).count()
    return bool(active >= settings.SBOM_MAX_CONCURRENT_JOBS_PER_ORG)


def submit_job(
    org: Org,
    user: UserT | None,
    *,
    file_obj: Any,
    application_id: str,
    component_name: str,
    repository_url: str,
    source_branch: str,
    output_format: str,
) -> tuple[SBOMJob, ManifestUpload]:
    """Gate, store the manifest, create the job, and dispatch the pipeline.

    The whole submission sequence, extracted in Story 21.9 so the DRF endpoint and the
    server-rendered page share one implementation rather than two that drift.

    The invariants live here and are not to be reproduced by callers:

    - **AD-7** — the concurrency gate is checked before anything is written.
    - **AD-12** — ``create_job`` performs the sole permitted non-Celery write of the initial
      ``PENDING`` status.
    - **AD-10** — dispatch is ``delay_on_commit``, so the worker cannot observe a job row
      that the surrounding transaction has not yet committed.

    Args:
        org: The organisation the job belongs to.
        user: The submitting user, or None for an API-key submission.
        file_obj: The uploaded manifest.
        application_id: Provenance — the owning application's identifier.
        component_name: Provenance — the component name.
        repository_url: Provenance — the source repository.
        source_branch: Provenance — the source branch.
        output_format: One of :data:`OUTPUT_FORMAT_MAP`'s keys.

    Returns:
        The created job and the stored manifest upload.

    Raises:
        ConcurrencyLimitError: If the org is already at its limit.
        UnsupportedFormatError: If the manifest's format cannot be detected.
        ManifestParseError: If the manifest cannot be parsed.
    """
    if at_concurrency_limit(org):
        raise ConcurrencyLimitError

    # Imported here rather than at module scope: inventory.tasks.sbom_pipeline imports from
    # this module, so a top-level import would be circular.
    from inventory.tasks.sbom_pipeline import run_sbom_pipeline

    with transaction.atomic():
        upload = upload_manifest(
            org,
            user,
            file_obj=file_obj,
            application_id=application_id,
            component_name=component_name,
            repository_url=repository_url,
            source_branch=source_branch,
        )
        job = create_job(org, upload, user, OUTPUT_FORMAT_MAP[output_format])
        run_sbom_pipeline.delay_on_commit(str(job.task_id))

    return job, upload


def create_job(org: Org, manifest: ManifestUpload, user: UserT | None, output_format: str) -> SBOMJob:
    """Create a PENDING job (the view's initial status write; AD-12)."""
    return SBOMJob.objects.create(
        org=org,
        manifest=manifest,
        user=user_ref(user),
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


def advance_job_progress(task_id: str, progress: int, current_step: str) -> None:
    """Name the phase doing the work, and move the bar forward only (Story 22.19).

    The two halves have **different rules**, which is the whole point of this function:

    * ``progress`` may only increase. The three analysis phases run concurrently in a chord
      whose order is undefined, and their bands are 55, 80 and 93, so a plain write can move
      the bar backwards — which reads as a broken job. ``Greatest`` keeps it monotonic inside
      the UPDATE itself, so two workers writing at the same instant cannot interleave into a
      regression.
    * ``current_step`` is always taken from the latest write. Guarding it by progress as well
      looked tidier and was wrong: version currency (93) wins the race against vulnerability
      scan (55) and licence compliance (80) within milliseconds, so those two phases never got
      to name themselves at all. A real job went ``45% → 93%`` and the label appeared frozen on
      "generate SBOM document" — the exact complaint this story exists to fix, reintroduced by
      the guard meant to fix it.

    The label therefore says what happened most recently, which is the honest answer while
    several phases are in flight, and changes visibly throughout the run. Under the Windows
    ``--pool=solo`` worker the phases are serial, so it is exact there.

    Only a pending or running job is eligible — a whitelist rather than "not terminal" so a
    status added later has to be considered. The chord callback can finalize while a group
    member is still unwinding, and a job that flips back to "In progress" after showing Success
    is worse than a stale percentage.
    """
    SBOMJob.objects.filter(
        task_id=task_id,
        status__in=(SBOMJob.Status.PENDING, SBOMJob.Status.PROGRESS),
    ).update(
        status=SBOMJob.Status.PROGRESS,
        progress=Greatest("progress", Value(progress)),
        current_step=current_step,
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
    """Lift the provenance fields off a manifest for SBOM metadata (FR-3.8, Story 22.14).

    The organization comes from the manifest's own ``org``, not from the acting request:
    ``org`` is what the upload form recorded at submission time, and the SBOM must say which
    line of business the job was filed against even when it is regenerated or exported later
    by someone acting elsewhere.
    """
    return Provenance(
        application_id=manifest.application_id,
        component_name=manifest.component_name,
        repository_url=manifest.repository_url,
        source_branch=manifest.source_branch,
        organization=manifest.org.name if manifest.org_id else "",
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
