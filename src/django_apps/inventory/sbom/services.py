"""Mutation services for the sbom app (AD-3).

``SBOMJob.status`` is written ONLY here (AD-12): task code calls
``update_job_status`` / ``finalize_job``; the generate view sets the initial
PENDING via ``create_job``. DRF views never write status otherwise.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime, timedelta
from typing import Any, cast

import structlog
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import QuerySet
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
from .models import JobTask, SBOMJob
from .parsers import PackageSpec, resolve_packages
from .pipeline_tasks import PIPELINE_TASKS, TASKS_BY_KEY, progress_for, task_label
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
    "delete_job_record",
    "delete_job_records",
    "estimate_seconds",
    "finalize_job",
    "generate_sbom_document",
    "mark_stale_job_timed_out",
    "presigned_artifact_url",
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
    """Create a PENDING job with its full task list (AD-12, Story 22.20)."""
    job = SBOMJob.objects.create(
        org=org,
        manifest=manifest,
        user=user_ref(user),
        output_format=output_format,
        status=SBOMJob.Status.PENDING,
    )
    seed_job_tasks(job)
    return job


def update_job_status(
    task_id: str,
    status: str,
    *,
    progress: int | None = None,
    current_step: str | None = None,
    failure_reason: str | None = None,
) -> None:
    """Update a job's status. The sole status writer for task code (AD-12).

    ``progress`` and ``current_step`` default to **None meaning "leave alone"**, not to ``0``
    and ``""`` meaning "reset". Every caller is a failure path that passes only a reason, and
    the old defaults quietly wiped both — so a job that failed at 62% on version currency
    displayed as 0% with no phase, discarding the one piece of information someone reading a
    failed job actually wants.
    """
    fields: dict[str, object] = {"status": status, "failure_reason": failure_reason}
    if progress is not None:
        fields["progress"] = progress
    if current_step is not None:
        fields["current_step"] = current_step
    SBOMJob.objects.filter(task_id=task_id).update(**fields)


def seed_job_tasks(job: SBOMJob) -> None:
    """Create the job's task rows, all pending (Story 22.20).

    Seeded up front rather than on first touch so the results page can show the **whole**
    pipeline from the moment a job is submitted — what is coming, not only what has happened.
    A watcher can see there are eight steps before any of them start.
    """
    with _reporting_is_best_effort("seed", str(job.task_id)):
        JobTask.objects.bulk_create(
            [JobTask(job=job, key=task.key, ordinal=task.ordinal) for task in PIPELINE_TASKS],
            ignore_conflicts=True,
        )


def _reporting_is_best_effort(operation: str, task_id: str) -> AbstractContextManager[None]:
    """Never let progress reporting abort the work it is reporting on (Story 22.20).

    Learned the hard way. ``start_job_task`` is called from ``_phase_guard`` *before* its
    ``try``, so anything it raised propagated out of the context manager's entry and skipped
    every failure path the guard exists to provide: the phase died, the job was never marked
    FAILED, and it sat at PENDING showing "Queued" with nothing to explain it. A developer who
    pulled migration ``0004`` without running it hit exactly that.

    Telemetry is not the work. A reporting failure degrades the display and is logged loudly;
    it must not cost the job.
    """
    return _swallow_reporting_error(operation, task_id)


@contextmanager
def _swallow_reporting_error(operation: str, task_id: str) -> Iterator[None]:
    """Log and continue. Deliberately broad: any reporting failure beats a lost job."""
    try:
        yield
    except Exception:
        logger.error("job_progress_report_failed", operation=operation, task_id=str(task_id), exc_info=True)


def _upsert_task(task_id: str, key: str, **fields: object) -> None:
    """Write one task's row, creating it if the job was never seeded.

    Seeding happens in :func:`create_job`, but a row that is merely *expected* to exist is a
    silent failure waiting to happen: the progress list renders empty and nothing says why.
    Creating on demand means a job submitted through any path still reports, and the unique
    constraint keeps a race between the start and finish writes from doubling the row.

    An unknown key is ignored rather than invented — it would have no place in the ordered
    list, and a task the pipeline does not declare should not be able to appear on screen.
    """
    task = TASKS_BY_KEY.get(key)
    if task is None:
        return
    job = SBOMJob.objects.filter(task_id=task_id).first()
    if job is None:
        return
    JobTask.objects.update_or_create(job=job, key=key, defaults={"ordinal": task.ordinal, **fields})


def _sync_job_progress(task_id: str, current_step: str | None = None) -> None:
    """Recompute the job's percentage from how many of its tasks have finished.

    Derived rather than reported, which is the point of Story 22.20: the old hand-picked bands
    (5, 20, 45, 55, 80, 93, 95, 97) drifted and collided — two different tasks both claimed 93%
    — so the bar and the label could disagree. Counting terminal rows cannot.

    ``SBOMJob.progress`` is kept up to date because the API exposes it (Story 21.24 AC #9) and
    the Job Status table shows a compact percentage beside each row.
    """
    finished = JobTask.objects.filter(job__task_id=task_id, state__in=JobTask.TERMINAL).count()
    fields: dict[str, object] = {"status": SBOMJob.Status.PROGRESS, "progress": progress_for(finished)}
    if current_step is not None:
        # Kept in step for the two surfaces that still want one line rather than a list: the
        # Job Status table's compact cell, and `current_phase` in the API's status payload,
        # which Story 21.24 AC #9 froze. With several tasks running, the most recently started
        # one is the summary — the results page's list is where the full truth lives.
        fields["current_step"] = current_step
    SBOMJob.objects.filter(
        task_id=task_id,
        status__in=(SBOMJob.Status.PENDING, SBOMJob.Status.PROGRESS),
    ).update(**fields)


def start_job_task(task_id: str, key: str) -> None:
    """Mark one task running, and stamp when it started.

    Each task writes only its **own** row, so the three concurrent analysis tasks cannot race
    each other — the reason this is a table rather than a field on the job.

    ``started_at`` records when the task began. The browser animates the dots from its own
    counter rather than from this stamp — deriving them from elapsed time made them jump — but
    the stamp is what tells an operator how long a task has been going.
    """
    with _reporting_is_best_effort("start", task_id):
        _upsert_task(task_id, key, state=JobTask.State.RUNNING, started_at=timezone.now(), finished_at=None, detail="")
        _sync_job_progress(task_id, current_step=task_label(key))


def finish_job_task(task_id: str, key: str, *, failed: bool = False, detail: str = "") -> None:
    """Mark one task finished, successfully or not, and advance the bar.

    An errored task still counts as finished: FR-4.5 keeps the job running when an analysis
    task fails, so a bar that stalled on it would misreport a job that is still working.
    """
    with _reporting_is_best_effort("finish", task_id):
        _upsert_task(
            task_id,
            key,
            state=JobTask.State.ERROR if failed else JobTask.State.COMPLETE,
            finished_at=timezone.now(),
            detail=detail[:200],
        )
        _sync_job_progress(task_id)


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


#: Presigned artifact URLs live for 24 hours (AD-11).
PRESIGN_TTL_SECONDS = 24 * 60 * 60


def presigned_artifact_url(key: str) -> str:
    """Return a presigned download URL for a stored artifact.

    Django never streams artifact bytes; callers redirect to this URL instead (AD-11). One
    implementation for both the API's 303 and the results page's download button, so the TTL
    cannot drift between them.
    """
    try:
        return default_storage.url(key, expire=PRESIGN_TTL_SECONDS)  # type: ignore[call-arg]
    except TypeError:
        # FileSystemStorage (dev/tests) has no presigning; url() takes only the name.
        return default_storage.url(key)


def delete_artifacts_for_jobs(jobs: Iterable[SBOMJob]) -> int:
    """Delete artifacts for each job via ``delete_job_artifacts``; return how many were purged.

    On-demand (Story 7.2) bulk primitive: reuses the single-job cleanup so there is no
    duplicated deletion logic (AD-3). Jobs already cleaned are skipped and not counted.
    """
    return sum(1 for job in jobs if delete_job_artifacts(job))


def delete_job_record(job: SBOMJob) -> None:
    """Delete a job outright: every blob it owns, then the row and everything hanging off it.

    Distinct from :func:`delete_job_artifacts`, which frees storage and keeps the record
    (FR-8.1). This is the record-level delete Job Status offers: the SBOM blob, the analysis
    report blobs, the uploaded manifest file, the ``AnalysisReport`` and ``JobTask`` rows (by
    cascade), the ``SBOMJob`` row, and the ``ManifestUpload`` row once no other job needs it.
    Irreversible — the caller is responsible for confirming.

    Blobs go first and the row last: a job row with a missing blob is a state the app already
    handles (Story 7.3), whereas a deleted row pointing at surviving blobs would leave storage
    with nothing left to name it.
    """
    keys = [key for key in (job.result_key, *(r.artifact_key for r in job.reports.all())) if key]
    manifest = job.manifest
    manifest_file = manifest.file.name if manifest and manifest.file else None
    # The manifest is shared if it has other jobs, so its file only goes with the last one.
    last_job_for_manifest = manifest is not None and not manifest.jobs.exclude(pk=job.pk).exists()
    if last_job_for_manifest and manifest_file:
        keys.append(manifest_file)

    for key in keys:
        if default_storage.exists(key):
            default_storage.delete(key)

    org_id = job.org_id
    task_id = str(job.task_id)
    with transaction.atomic():
        # Cascades to JobTask and AnalysisReport rows.
        SBOMJob.objects.filter(task_id=job.task_id).delete()
        if last_job_for_manifest and manifest is not None:
            ManifestUpload.objects.filter(pk=manifest.pk).delete()
    logger.info("job_record_deleted", task_id=task_id, org_id=org_id, blobs=len(keys))


def delete_job_records(jobs: Iterable[SBOMJob]) -> int:
    """Delete each job record via :func:`delete_job_record`; return how many were removed.

    Bulk primitive behind Job Status's delete actions, reusing the single-job path so there is
    one implementation of what "delete the record" means (AD-3).
    """
    deleted = 0
    for job in jobs:
        delete_job_record(job)
        deleted += 1
    return deleted


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
