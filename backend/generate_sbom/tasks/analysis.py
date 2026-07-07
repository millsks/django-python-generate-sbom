"""Celery analysis tasks (analysis queue, AD-4).

Phases 4, 5, and 7 run on the ``analysis`` queue. Each task returns the standard chord
envelope and NEVER raises on an analysis failure — a failed report leaves the job
SUCCESS with the SBOM + partial reports (FR-4.5). Story 4.6 wires these into the
pipeline chord, replacing the Epic 3 no-op stubs.

Analysis tasks reload the resolved package list via ``resolve_job_packages`` (the
generate ctx carries only keys/counts, AD-6); 4.6 may optimize the hand-off.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import structlog
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from generate_sbom.analysis.services import license as license_service
from generate_sbom.analysis.services import versions as versions_service
from generate_sbom.analysis.services import vulnerability
from generate_sbom.analysis.services.reports import make_envelope
from generate_sbom.sbom.parsers import PackageSpec
from generate_sbom.sbom.selectors import get_job_by_task_id
from generate_sbom.sbom.services import resolve_job_packages

logger = structlog.get_logger()

_ReportBuilder = Callable[[list[PackageSpec]], dict[str, Any]]


def _run_phase(
    task: Any,
    ctx: dict[str, Any],
    *,
    report_type: str,
    filename: str,
    builder: _ReportBuilder,
    start_pct: int,
    end_pct: int,
    step: str,
    fail_reason: str,
) -> dict[str, Any]:
    """Run one analysis phase: build the report, persist it, and return the chord envelope.

    A failure (including a soft timeout) yields a ``failed`` envelope rather than
    raising, so the chord/job still completes with the SBOM (FR-4.5).
    """
    task_id = ctx["task_id"]
    task.update_state(state="PROGRESS", meta={"progress": start_pct, "current_step": step})
    job = get_job_by_task_id(task_id)
    started = time.monotonic()
    try:
        packages = resolve_job_packages(task_id)
        report = builder(packages)
        artifact_key = f"sbom-results/{job.org_id}/{task_id}/{filename}"
        if default_storage.exists(artifact_key):
            default_storage.delete(artifact_key)
        default_storage.save(artifact_key, ContentFile(json.dumps(report, indent=2).encode("utf-8")))
        envelope = make_envelope(report_type, artifact_key=artifact_key, summary=report["summary"])
        logger.info(
            f"phase_{report_type}",
            task_id=str(task_id),
            org_id=job.org_id,
            duration_s=round(time.monotonic() - started, 3),
            package_count=len(packages),
            summary=report["summary"],
        )
    except SoftTimeLimitExceeded:
        logger.error(f"phase_{report_type}_timeout", task_id=str(task_id), org_id=job.org_id, exc_info=True)
        envelope = make_envelope(report_type, failed=True, failure_reason="timeout")
    except Exception as exc:  # analysis failures never abort the chord (FR-4.5)
        logger.error(
            f"phase_{report_type}_failed", task_id=str(task_id), org_id=job.org_id, error=str(exc), exc_info=True
        )
        envelope = make_envelope(report_type, failed=True, failure_reason=fail_reason)

    task.update_state(state="PROGRESS", meta={"progress": end_pct, "current_step": f"{step} complete"})
    return envelope


@shared_task(bind=True, queue="analysis")  # type: ignore[untyped-decorator]
def scan_vulnerabilities(self: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """Phase 4 (55-80%): scan resolved packages for known vulnerabilities (OSV + NVD)."""
    return _run_phase(
        self,
        ctx,
        report_type="vuln",
        filename="vuln.json",
        builder=vulnerability.scan,
        start_pct=55,
        end_pct=80,
        step="vulnerability scan",
        fail_reason="vulnerability_scan_failed",
    )


@shared_task(bind=True, queue="analysis")  # type: ignore[untyped-decorator]
def classify_licenses(self: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """Phase 5 (80-88%): classify each package's license into legal-risk tiers."""
    return _run_phase(
        self,
        ctx,
        report_type="license",
        filename="licenses.json",
        builder=license_service.classify,
        start_pct=80,
        end_pct=88,
        step="license compliance",
        fail_reason="license_classification_failed",
    )


@shared_task(bind=True, queue="analysis")  # type: ignore[untyped-decorator]
def check_version_currency(self: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """Phase 7 (93-97%): classify each package's version currency against PyPI + LTS."""
    return _run_phase(
        self,
        ctx,
        report_type="version",
        filename="versions.json",
        builder=versions_service.classify,
        start_pct=93,
        end_pct=97,
        step="version currency",
        fail_reason="version_currency_failed",
    )
