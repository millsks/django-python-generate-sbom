"""Tests for the Phase 1/2 task bodies and resolve_job_packages (Story 3.3)."""

import pytest
from django.core.files.base import ContentFile

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import JobTask, SBOMJob
from inventory.sbom.services import resolve_job_packages
from inventory.tasks.sbom_pipeline import detect_and_parse_manifest, resolve_transitive_deps
from inventory.users.services import create_org, register_user

PIXI_LOCK = b"""
version: 5
packages:
  - name: numpy
    version: "1.26.0"
  - name: requests
    version: "2.32.3"
"""


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
        application_id="APP-1",
        component_name="web",
        repository_url="https://github.com/acme/web",
        source_branch="main",
    )
    upload.file.save("pixi.lock", ContentFile(PIXI_LOCK), save=False)
    upload.save()
    return SBOMJob.objects.create(org=org, manifest=upload, output_format="cyclonedx-json")


@pytest.mark.django_db
def test_resolve_job_packages_reads_pixi_lock() -> None:
    job = _make_job()
    packages = resolve_job_packages(str(job.task_id))
    assert {p.name for p in packages} == {"numpy", "requests"}


@pytest.mark.django_db
def test_phase_functions_report_progress_and_shape() -> None:
    """Story 22.20 changed *where* a phase reports: its own task row, not `update_state`.

    The old assertion was `update_state.called`, which only proved a phase told Celery's result
    backend something. What the user sees comes from the task rows, so that is what is asserted
    — and both phases must reach COMPLETE, not merely have started.
    """
    job = _make_job()

    phase1 = detect_and_parse_manifest.apply(args=(str(job.task_id),)).get()
    phase2 = resolve_transitive_deps.apply(args=(phase1,)).get()

    assert phase1["detected_format"] == "pixi_lock"
    assert {pkg["name"] for pkg in phase2["packages"]} == {"numpy", "requests"}

    states = {task.key: task.state for task in job.tasks.all()}
    assert states["detect"] == JobTask.State.COMPLETE
    assert states["resolve"] == JobTask.State.COMPLETE
