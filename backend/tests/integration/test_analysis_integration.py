"""Integration: the full pipeline with the real analysis group (Story 4.6).

Runs every phase in chain order (the eager chord needs a live result backend, so
we drive the sequence directly — see Story 3.5). Analysis *services* are patched to
canned outputs so no network is needed; the task/aggregate/persist wiring is real.
"""

from contextlib import ExitStack
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from generate_sbom.analysis.models import AnalysisReport
from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.tasks.analysis import (
    check_version_currency,
    classify_licenses,
    scan_vulnerabilities,
)
from generate_sbom.tasks.sbom_pipeline import (
    aggregate_analysis_results,
    detect_and_parse_manifest,
    generate_sbom_document,
    persist_artifacts,
    resolve_transitive_deps,
)
from generate_sbom.users.services import create_org, register_user

_NO_UPDATE = "celery.app.task.Task.update_state"
PIXI_LOCK = b'version: 5\npackages:\n  - name: numpy\n    version: "1.26.0"\n'
_ANALYSIS_TASKS = (scan_vulnerabilities, classify_licenses, check_version_currency)


def _make_job() -> SBOMJob:
    user = register_user(email="alice@example.com", password="pw12345678")
    org = create_org(name=user.email.split("@")[0], admin_user=user)
    upload = ManifestUpload(
        org=org,
        user=user,
        detected_format=ManifestUpload.Format.PIXI_LOCK,
        original_filename="pixi.lock",
        application_id="A",
        component_name="c",
        repository_url="https://github.com/a/b",
        source_branch="main",
    )
    upload.file.save("pixi.lock", ContentFile(PIXI_LOCK), save=False)
    upload.save()
    return SBOMJob.objects.create(org=org, manifest=upload, output_format="cyclonedx-json")


def _run_pipeline(task_id: str) -> None:
    detected = detect_and_parse_manifest.apply(args=(task_id,)).get()
    resolved = resolve_transitive_deps.apply(args=(detected,)).get()
    generated = generate_sbom_document.apply(args=(resolved,)).get()
    envelopes = [task.apply(args=(generated,)).get() for task in _ANALYSIS_TASKS]
    aggregate_analysis_results.apply(args=(envelopes, task_id)).get()
    persist_artifacts.apply(args=(task_id,)).get()


def _patch_services(stack: ExitStack, *, vuln_fails: bool = False) -> None:
    vuln = stack.enter_context(patch("generate_sbom.analysis.services.vulnerability.scan"))
    if vuln_fails:
        vuln.side_effect = RuntimeError("osv down")
    else:
        vuln.return_value = {"summary": {"vulnerable_package_count": 0, "severity_breakdown": {}}}
    stack.enter_context(
        patch("generate_sbom.analysis.services.license.classify", return_value={"summary": {"Permissive": 1}})
    )
    stack.enter_context(
        patch("generate_sbom.analysis.services.versions.classify", return_value={"summary": {"current": 1}})
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_full_pipeline_all_success(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]
    job = _make_job()

    with ExitStack() as stack:
        stack.enter_context(patch(_NO_UPDATE))
        _patch_services(stack)
        _run_pipeline(str(job.task_id))

    job.refresh_from_db()
    assert job.status == SBOMJob.Status.SUCCESS
    assert default_storage.exists(job.result_key)  # SBOM downloadable

    reports = {r.report_type: r for r in AnalysisReport.objects.filter(job=job)}
    assert set(reports) == {"vuln", "license", "version"}
    assert all(not r.failed and r.artifact_key for r in reports.values())


@pytest.mark.integration
@pytest.mark.django_db
def test_full_pipeline_partial_failure_keeps_sbom(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]
    job = _make_job()

    with ExitStack() as stack:
        stack.enter_context(patch(_NO_UPDATE))
        _patch_services(stack, vuln_fails=True)  # only the vulnerability phase fails
        _run_pipeline(str(job.task_id))

    job.refresh_from_db()
    # Job still completes with a downloadable SBOM (FR-4.5).
    assert job.status == SBOMJob.Status.SUCCESS
    assert default_storage.exists(job.result_key)

    reports = {r.report_type: r for r in AnalysisReport.objects.filter(job=job)}
    assert reports["vuln"].failed is True
    assert reports["vuln"].failure_reason == "vulnerability_scan_failed"
    assert all(not reports[rt].failed for rt in ("license", "version"))

    # The failed-report endpoint conveys the reason (AC #6).
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": "pw12345678"}, format="json")
    response = client.get(f"/api/v1/sbom/result/{job.task_id}/reports/vulnerabilities/")
    assert response.status_code == 404
    assert response.data["code"] == "report_failed"
    assert response.data["failure_reason"] == "vulnerability_scan_failed"
