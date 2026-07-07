"""Tests for the AnalysisReport model + envelope/report helpers (Story 4.1)."""

import pytest
from django.core.files.base import ContentFile

from generate_sbom.analysis.models import AnalysisReport
from generate_sbom.analysis.services.reports import make_envelope, write_report
from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.users.services import create_org, register_user


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


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
    upload.file.save("pixi.lock", ContentFile(b"version: 5\n"), save=False)
    upload.save()
    return SBOMJob.objects.create(org=org, manifest=upload, output_format="cyclonedx-json")


def test_make_envelope_defaults() -> None:
    assert make_envelope("vuln") == {
        "report_type": "vuln",
        "artifact_key": None,
        "summary": {},
        "failed": False,
        "failure_reason": None,
    }


def test_make_envelope_failed() -> None:
    envelope = make_envelope("license", failed=True, failure_reason="osv timeout")
    assert envelope["failed"] is True
    assert envelope["failure_reason"] == "osv timeout"
    assert envelope["summary"] == {}


@pytest.mark.django_db
def test_write_report_persists_from_envelope() -> None:
    job = _make_job()
    envelope = make_envelope("vuln", artifact_key="sbom-results/x/vuln.json", summary={"total": 3})

    report = write_report(job, envelope)

    report.refresh_from_db()
    assert report.report_type == AnalysisReport.ReportType.VULN
    assert report.artifact_key == "sbom-results/x/vuln.json"
    assert report.summary == {"total": 3}
    assert report.failed is False
    assert report.generated_at is not None
    # Reachable (and org-scoped) only through the parent job.
    assert list(job.reports.all()) == [report]


@pytest.mark.django_db
def test_write_failed_report() -> None:
    job = _make_job()
    report = write_report(job, make_envelope("version", failed=True, failure_reason="solver error"))
    assert report.failed is True
    assert report.failure_reason == "solver error"
    assert report.artifact_key is None


@pytest.mark.django_db
def test_write_report_upserts_per_job_report_type() -> None:
    job = _make_job()
    first = write_report(job, make_envelope("vuln", failed=True, failure_reason="osv down"))
    # A chord re-run overwrites the same (job, report_type) row rather than conflicting.
    second = write_report(job, make_envelope("vuln", artifact_key="k", summary={"total": 2}))

    assert second.pk == first.pk
    assert AnalysisReport.objects.filter(job=job, report_type="vuln").count() == 1
    second.refresh_from_db()
    assert second.failed is False
    assert second.artifact_key == "k"
    assert second.summary == {"total": 2}
