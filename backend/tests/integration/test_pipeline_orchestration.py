"""Integration: the full eight-phase pipeline run end to end (Story 3.5).

Executes every phase body in chain order against real filesystem storage and the
DB, asserting the job reaches SUCCESS with monotonic progress. Chord/broker wiring
is validated structurally in the unit shape test; here we validate that the phase
bodies compose correctly and the data contracts between them hold.
"""

import time
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom import services
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.tasks import sbom_pipeline as pipeline
from generate_sbom.users.services import register_user

_NO_UPDATE = "celery.app.task.Task.update_state"
PIXI_LOCK = (
    b'version: 5\npackages:\n  - name: numpy\n    version: "1.26.0"\n  - name: requests\n    version: "2.32.3"\n'
)
ANALYSIS_TASKS = (
    pipeline.scan_vulnerabilities,
    pipeline.analyze_licenses,
    pipeline.build_dependency_graph,
    pipeline.check_version_currency,
)


def _make_job(output_format: str) -> SBOMJob:
    user = register_user(email="alice@example.com", password="pw12345678")
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
    upload.file.save("pixi.lock", ContentFile(PIXI_LOCK), save=False)
    upload.save()
    return SBOMJob.objects.create(org=org, manifest=upload, output_format=output_format)


@pytest.mark.integration
@pytest.mark.django_db
def test_full_pipeline_sequence_succeeds(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]
    job = _make_job("cyclonedx-json")

    seen: list[int] = []
    real_update = services.update_job_status

    def _record(task_id: str, status: str, **kwargs: object) -> None:
        seen.append(kwargs.get("progress"))  # type: ignore[arg-type]
        real_update(task_id, status, **kwargs)  # type: ignore[arg-type]

    started = time.perf_counter()
    with patch(_NO_UPDATE), patch.object(services, "update_job_status", side_effect=_record):
        detected = pipeline.detect_and_parse_manifest.apply(args=(str(job.task_id),)).get()
        resolved = pipeline.resolve_transitive_deps.apply(args=(detected,)).get()
        generated = pipeline.generate_sbom_document.apply(args=(resolved,)).get()
        envelopes = [task.apply(args=(generated,)).get() for task in ANALYSIS_TASKS]
        pipeline.aggregate_analysis_results.apply(args=(envelopes, str(job.task_id))).get()
        pipeline.persist_artifacts.apply(args=(str(job.task_id),)).get()
    elapsed = time.perf_counter() - started

    job.refresh_from_db()
    assert job.status == SBOMJob.Status.SUCCESS
    assert job.progress == 100
    assert job.summary_stats == {"total_packages": 2}
    assert job.artifacts_expire_at is not None
    assert default_storage.exists(job.result_key)

    # Analysis stubs return empty, non-failed envelopes (AC #2).
    assert all(env["failed"] is False and env["summary"] == {} for env in envelopes)
    # Mirrored progress is monotonically increasing (AC #3).
    assert seen == sorted(seen)
    # <50-package fixture completes well within the NFR-2.1 target (AC #9).
    assert elapsed < 35
