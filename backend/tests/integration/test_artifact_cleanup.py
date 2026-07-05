"""Integration: the artifact purge deletes real blobs and retains job metadata (Story 7.1).

Dev/test storage is the filesystem (FileSystemStorage → MEDIA_ROOT); the delete code
path is identical for MinIO/S3 in production (AD-6). Real blob write and delete, no
mocked infrastructure.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from generate_sbom.analysis.models import AnalysisReport
from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.sbom.services import purge_expired_artifacts
from generate_sbom.users.services import register_user


@pytest.mark.integration
@pytest.mark.django_db
def test_purge_deletes_real_blobs_and_keeps_metadata(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]
    user = register_user(email=f"{uuid4().hex}@example.com", password="pw12345678")
    org = user.org_memberships.select_related("org").get().org
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
    upload.file.save("pixi.lock", ContentFile(b"version: 5\n"), save=False)
    upload.save()
    sbom_key = default_storage.save(f"sbom-results/{uuid4().hex}/sbom.json", ContentFile(b"{}"))
    job = SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        result_key=sbom_key,
        summary_stats={"total_packages": 2},
        completed_at=timezone.now(),
        artifacts_expire_at=timezone.now() - timedelta(days=1),
    )
    report_key = default_storage.save(f"reports/{uuid4().hex}/vuln.json", ContentFile(b"{}"))
    AnalysisReport.objects.create(
        job=job,
        report_type=AnalysisReport.ReportType.VULN,
        artifact_key=report_key,
        summary={"vulnerable_package_count": 0},
    )
    assert default_storage.exists(sbom_key)
    assert default_storage.exists(report_key)

    assert purge_expired_artifacts() == 1

    assert not default_storage.exists(sbom_key)
    assert not default_storage.exists(report_key)
    job.refresh_from_db()
    assert job.result_key is None
    assert job.status == SBOMJob.Status.SUCCESS
    assert job.summary_stats == {"total_packages": 2}
