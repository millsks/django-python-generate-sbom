"""Tests for pipeline orchestration, progress, and timeout handling (Story 3.5)."""

from dataclasses import asdict
from datetime import timedelta
from unittest.mock import patch

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings as conf
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework.test import APIClient

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.parsers import PackageSpec, ResolutionError
from generate_sbom.tasks import sbom_pipeline as pipeline
from generate_sbom.users.services import create_org, register_user

_NO_UPDATE = "celery.app.task.Task.update_state"
PIXI_LOCK = (
    b'version: 5\npackages:\n  - name: numpy\n    version: "1.26.0"\n  - name: requests\n    version: "2.32.3"\n'
)
PKGS = [PackageSpec(name="numpy", version="1.26.0"), PackageSpec(name="requests", version="2.32.3")]
ANALYSIS_TASKS = (
    pipeline.scan_vulnerabilities,
    pipeline.classify_licenses,
    pipeline.check_version_currency,
)


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _make_job(output_format: str = "cyclonedx-json", email: str = "alice@example.com") -> SBOMJob:
    user = register_user(email=email, password="pw12345678")
    org = create_org(name=user.email.split("@")[0], admin_user=user)
    upload = ManifestUpload(
        org=org,
        user=user,
        detected_format=ManifestUpload.Format.PIXI_LOCK,
        original_filename="pixi.lock",
        application_id="APP-1",
        component_name="web",
        repository_url="https://github.com/acme/web",
        source_branch="main",
    )
    upload.file.save("pixi.lock", ContentFile(PIXI_LOCK), save=False)
    upload.save()
    return SBOMJob.objects.create(org=org, manifest=upload, output_format=output_format)


def _login(email: str = "alice@example.com") -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": "pw12345678"}, format="json")
    return client


# --- Canvas shape & routing (AC #1, #2, #8) ------------------------------------------


def test_pipeline_canvas_shape() -> None:
    canvas = pipeline.build_pipeline("t")
    assert [t.name.split(".")[-1] for t in canvas.tasks[:3]] == [
        "detect_and_parse_manifest",
        "resolve_transitive_deps",
        "generate_sbom_document",
    ]
    chord_el = canvas.tasks[3]
    assert chord_el["subtask_type"] == "chord"
    # The three real analysis tasks (the dependency-graph phase was retired in Story 20.1).
    assert [t.name.split(".")[-1] for t in chord_el.tasks] == [
        "scan_vulnerabilities",
        "classify_licenses",
        "check_version_currency",
    ]
    assert [t.name.split(".")[-1] for t in chord_el.body.tasks] == [
        "aggregate_analysis_results",
        "persist_artifacts",
    ]


def test_queue_routing() -> None:
    for task in (
        pipeline.detect_and_parse_manifest,
        pipeline.resolve_transitive_deps,
        pipeline.generate_sbom_document,
        pipeline.aggregate_analysis_results,
        pipeline.persist_artifacts,
    ):
        assert task.queue == "pipeline"
    for task in ANALYSIS_TASKS:
        assert task.queue == "analysis"


def test_run_sbom_pipeline_dispatches_chain() -> None:
    with patch.object(pipeline, "build_pipeline") as build:
        pipeline.run_sbom_pipeline.apply(args=("tid",)).get()
    build.assert_called_once_with("tid")
    build.return_value.delay.assert_called_once_with()


# --- Chord callback: report persistence (Story 4.6) ----------------------------------


@pytest.mark.django_db
def test_aggregate_writes_reports_and_merges_summaries() -> None:
    from generate_sbom.analysis.models import AnalysisReport

    job = _make_job()
    envelopes = [
        {
            "report_type": "vuln",
            "artifact_key": "k",
            "summary": {"vulnerable_package_count": 1},
            "failed": False,
            "failure_reason": None,
        },
        {"report_type": "license", "artifact_key": None, "summary": {}, "failed": True, "failure_reason": "pypi down"},
        {
            "report_type": "version",
            "artifact_key": "v",
            "summary": {"outdated_package_count": 2},
            "failed": False,
            "failure_reason": None,
        },
    ]
    out = pipeline.aggregate_analysis_results.apply(args=(envelopes, str(job.task_id))).get()

    assert out == {"task_id": str(job.task_id), "analysis": envelopes}
    job.refresh_from_db()
    assert job.progress == 95

    reports = {r.report_type: r for r in AnalysisReport.objects.filter(job=job)}
    assert reports["vuln"].failed is False and reports["vuln"].artifact_key == "k"
    assert reports["license"].failed is True and reports["license"].failure_reason == "pypi down"

    # summary_stats.reports carries each report's counts + failed flags.
    merged = job.summary_stats["reports"]
    assert merged["vuln"] == {"failed": False, "failure_reason": None, "vulnerable_package_count": 1}
    assert merged["license"] == {"failed": True, "failure_reason": "pypi down"}
    assert merged["version"] == {"failed": False, "failure_reason": None, "outdated_package_count": 2}


# --- Timeout handling (AC #4, #5, #6) ------------------------------------------------


@pytest.mark.django_db
def test_soft_timeout_marks_failed_no_artifact() -> None:
    job = _make_job()
    prev = {"task_id": str(job.task_id), "packages": [asdict(pkg) for pkg in PKGS]}
    with (
        patch(_NO_UPDATE),
        patch("generate_sbom.sbom.services.generate_sbom_document", side_effect=SoftTimeLimitExceeded()),
    ):
        result = pipeline.generate_sbom_document.apply(args=(prev,))

    assert result.failed()
    job.refresh_from_db()
    assert job.status == SBOMJob.Status.FAILED
    assert job.failure_reason == "soft_timeout"
    assert not default_storage.exists(f"sbom-results/{job.org_id}/{job.task_id}/sbom.json")


@pytest.mark.django_db
def test_hard_timeout_sweep_marks_failed_via_status() -> None:
    job = _make_job()  # PENDING
    stale = timezone.now() - timedelta(seconds=conf.CELERY_TASK_TIME_LIMIT + 60)
    SBOMJob.objects.filter(task_id=job.task_id).update(created_at=stale)

    response = _login().get(f"/api/v1/sbom/status/{job.task_id}/")

    assert response.data["status"] == SBOMJob.Status.FAILED
    assert response.data["failure_reason"] == "hard_timeout"


@pytest.mark.django_db
def test_persist_without_recorded_key_fails() -> None:
    job = _make_job()  # Phase 3 never ran, so no result_key was recorded.
    with patch(_NO_UPDATE):
        result = pipeline.persist_artifacts.apply(args=(str(job.task_id),))
    assert result.failed()
    job.refresh_from_db()
    assert job.status == SBOMJob.Status.FAILED
    assert job.failure_reason == "missing_artifact"


@pytest.mark.django_db
def test_status_before_hard_limit_is_untouched() -> None:
    job = _make_job()
    response = _login().get(f"/api/v1/sbom/status/{job.task_id}/")
    assert response.data["status"] == SBOMJob.Status.PENDING
    assert response.data["failure_reason"] is None


@pytest.mark.django_db
def test_resolution_error_marks_failed_not_stuck() -> None:
    # An unsatisfiable manifest (e.g. conflicting pins) must fail the job, not leave
    # it stuck at PROGRESS with the UI polling forever.
    job = _make_job()
    prev = {"task_id": str(job.task_id), "detected_format": "requirements"}
    with (
        patch(_NO_UPDATE),
        patch("generate_sbom.sbom.services.resolve_job_packages", side_effect=ResolutionError("unsatisfiable")),
    ):
        result = pipeline.resolve_transitive_deps.apply(args=(prev,))

    assert result.failed()
    job.refresh_from_db()
    assert job.status == SBOMJob.Status.FAILED
    assert job.failure_reason == "resolution_failed"


@pytest.mark.django_db
def test_unexpected_phase_error_falls_back_to_pipeline_error() -> None:
    # Safety net: a phase that raises without setting its own reason still finalizes
    # the job as FAILED rather than leaving it at PROGRESS.
    job = _make_job()
    prev = {"task_id": str(job.task_id), "detected_format": "requirements"}
    with (
        patch(_NO_UPDATE),
        patch("generate_sbom.sbom.services.resolve_job_packages", side_effect=ValueError("boom")),
    ):
        result = pipeline.resolve_transitive_deps.apply(args=(prev,))

    assert result.failed()
    job.refresh_from_db()
    assert job.status == SBOMJob.Status.FAILED
    assert job.failure_reason == "pipeline_error"
