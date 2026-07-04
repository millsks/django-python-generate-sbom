"""Tests for the Phase 6 task and the graph report endpoints (Story 4.4)."""

from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from generate_sbom.analysis.models import AnalysisReport
from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.sbom.models import SBOMJob
from generate_sbom.tasks.analysis import build_dependency_graph
from generate_sbom.users.services import register_user

_NO_UPDATE = "celery.app.task.Task.update_state"
PIXI_LOCK = b'version: 5\npackages:\n  - name: requests\n    version: "2.32.3"\n'
_CYTO = {
    "nodes": [{"data": {"id": "requests==2.32.3", "label": "requests", "version": "2.32.3"}}],
    "edges": [{"data": {"source": "requests==2.32.3", "target": "urllib3==2.3.0"}}],
}
_SVG = b'<?xml version="1.0"?><svg></svg>'


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _make_job(email: str = "alice@example.com") -> SBOMJob:
    user = register_user(email=email, password="pw12345678")
    org = user.org_memberships.select_related("org").get().org
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


def _login(email: str = "alice@example.com") -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": "pw12345678"}, format="json")
    return client


@pytest.mark.django_db
def test_phase6_writes_svg_and_returns_graph_summary() -> None:
    job = _make_job()
    with patch(_NO_UPDATE), patch("generate_sbom.tasks.analysis.graph_service.build", return_value=(_CYTO, _SVG)):
        envelope = build_dependency_graph.apply(args=({"task_id": str(job.task_id)},)).get()

    artifact_key = f"sbom-results/{job.org_id}/{job.task_id}/graph.svg"
    assert envelope["report_type"] == "graph"
    assert envelope["artifact_key"] == artifact_key
    assert envelope["summary"] == {"node_count": 1, "edge_count": 1, "nodes": _CYTO["nodes"], "edges": _CYTO["edges"]}
    assert envelope["failed"] is False
    with default_storage.open(artifact_key) as handle:
        assert handle.read() == _SVG


@pytest.mark.django_db
def test_phase6_failure_returns_failed_envelope() -> None:
    job = _make_job()
    with (
        patch(_NO_UPDATE),
        patch("generate_sbom.tasks.analysis.graph_service.build", side_effect=RuntimeError("graphviz down")),
    ):
        envelope = build_dependency_graph.apply(args=({"task_id": str(job.task_id)},)).get()

    assert envelope["failed"] is True
    assert envelope["failure_reason"] == "graph_build_failed"


@pytest.mark.django_db
def test_graph_json_endpoint_returns_nodes_and_edges() -> None:
    job = _make_job()
    AnalysisReport.objects.create(
        job=job,
        report_type=AnalysisReport.ReportType.GRAPH,
        artifact_key="k",
        summary={"node_count": 1, "edge_count": 1, "nodes": _CYTO["nodes"], "edges": _CYTO["edges"]},
    )

    response = _login().get(f"/api/v1/sbom/result/{job.task_id}/reports/graph/")

    assert response.status_code == 200
    assert response.data == {"nodes": _CYTO["nodes"], "edges": _CYTO["edges"]}


@pytest.mark.django_db
def test_graph_svg_download_303_and_cross_org_404() -> None:
    job = _make_job()
    artifact_key = f"sbom-results/{job.org_id}/{job.task_id}/graph.svg"
    default_storage.save(artifact_key, ContentFile(_SVG))
    AnalysisReport.objects.create(
        job=job,
        report_type=AnalysisReport.ReportType.GRAPH,
        artifact_key=artifact_key,
        summary={"nodes": [], "edges": []},
    )

    ok = _login().get(f"/api/v1/sbom/result/{job.task_id}/reports/graph/download/")
    assert ok.status_code == 303
    assert artifact_key in ok.headers["Location"]

    register_user(email="bob@example.com", password="pw12345678")
    cross = _login("bob@example.com").get(f"/api/v1/sbom/result/{job.task_id}/reports/graph/")
    assert cross.status_code == 404
