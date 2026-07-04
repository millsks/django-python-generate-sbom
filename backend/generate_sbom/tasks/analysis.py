"""Celery analysis tasks (analysis queue, AD-4).

Phases 4-7 run on the ``analysis`` queue. Each task returns the standard chord
envelope and NEVER raises on an analysis failure — a failed report leaves the job
SUCCESS with the SBOM + partial reports (FR-4.5). Story 4.6 wires these into the
pipeline chord, replacing the Epic 3 no-op stubs.

Analysis tasks reload the resolved package list via ``resolve_job_packages`` (the
generate ctx carries only keys/counts, AD-6); 4.6 may optimize the hand-off.
"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from generate_sbom.analysis.services import vulnerability
from generate_sbom.analysis.services.reports import make_envelope
from generate_sbom.sbom.selectors import get_job_by_task_id
from generate_sbom.sbom.services import resolve_job_packages

logger = structlog.get_logger()


@shared_task(bind=True, queue="analysis")  # type: ignore[untyped-decorator]
def scan_vulnerabilities(self: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """Phase 4 (55-80%): scan resolved packages for known vulnerabilities (OSV + NVD)."""
    task_id = ctx["task_id"]
    self.update_state(state="PROGRESS", meta={"progress": 55, "current_step": "vulnerability scan"})
    job = get_job_by_task_id(task_id)
    started = time.monotonic()
    try:
        packages = resolve_job_packages(task_id)
        report = vulnerability.scan(packages)
        artifact_key = f"sbom-results/{job.org_id}/{task_id}/vuln.json"
        if default_storage.exists(artifact_key):
            default_storage.delete(artifact_key)
        default_storage.save(artifact_key, ContentFile(json.dumps(report, indent=2).encode("utf-8")))
        envelope = make_envelope("vuln", artifact_key=artifact_key, summary=report["summary"])
        logger.info(
            "phase_vuln",
            task_id=str(task_id),
            org_id=job.org_id,
            duration_s=round(time.monotonic() - started, 3),
            package_count=len(packages),
            vulnerable_count=report["summary"]["vulnerable_package_count"],
        )
    except SoftTimeLimitExceeded:
        logger.error("phase_vuln_timeout", task_id=str(task_id), org_id=job.org_id, exc_info=True)
        envelope = make_envelope("vuln", failed=True, failure_reason="timeout")
    except Exception as exc:  # analysis failures never abort the chord (FR-4.5)
        logger.error("phase_vuln_failed", task_id=str(task_id), org_id=job.org_id, error=str(exc), exc_info=True)
        envelope = make_envelope("vuln", failed=True, failure_reason="vulnerability_scan_failed")

    self.update_state(state="PROGRESS", meta={"progress": 80, "current_step": "vulnerability scan complete"})
    return envelope
