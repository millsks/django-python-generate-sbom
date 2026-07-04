"""Mutation services for the sbom app (AD-3).

``SBOMJob.status`` is written ONLY here (AD-12): task code calls
``update_job_status`` / ``finalize_job``; the generate view sets the initial
PENDING via ``create_job``. DRF views never write status otherwise.
"""

from __future__ import annotations

from datetime import timedelta

import structlog
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
    "estimate_seconds",
    "finalize_job",
    "generate_sbom_document",
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
ARTIFACT_TTL_DAYS = 10


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


def finalize_job(task_id: str, result_key: str, summary_stats: dict[str, object]) -> None:
    """Mark a job SUCCESS with its artifact key and set the 10-day expiry (AD-12)."""
    now = timezone.now()
    SBOMJob.objects.filter(task_id=task_id).update(
        status=SBOMJob.Status.SUCCESS,
        progress=100,
        result_key=result_key,
        summary_stats=summary_stats,
        completed_at=now,
        artifacts_expire_at=now + timedelta(days=ARTIFACT_TTL_DAYS),
    )


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
