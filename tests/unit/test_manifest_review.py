"""Story 22.26: the Job Status table names the application, and links to the manifest.

Two gaps, both about being able to tell one job from another. The table showed the
organization and the manifest's *filename*, which is often the same string on every row —
`requirements.txt` says nothing about which application it came from. And the manifest itself
was write-only: uploaded, parsed, and then unreachable, so a surprising SBOM could not be
checked against the input that produced it.

The manifest is **user-uploaded content**, which is why it is rendered into an escaped
`<pre>` on a normal page rather than served as a file. A raw response would let an upload
choose its own content type, and the whole point here is to read it, not to download it.
"""

from __future__ import annotations

import pytest
from django.core.files.base import ContentFile
from django.test import Client

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org

pytestmark = pytest.mark.django_db

REQUIREMENTS = b"django==5.2.1\nrequests==2.32.3\n"


def _job(org: Org, *, body: bytes = REQUIREMENTS, application: str = "APP-42", component: str = "billing-api"):  # type: ignore[no-untyped-def]
    upload = ManifestUpload(
        org=org,
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
        application_id=application,
        component_name=component,
        repository_url="https://example.com/acme/billing",
        source_branch="main",
    )
    upload.file.save("requirements.txt", ContentFile(body), save=False)
    upload.save()
    return SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        summary_stats={},
        result_key="sboms/x.json",
    )


# --- The columns ------------------------------------------------------------------------------


def test_the_table_shows_the_application_and_component(default_org: Org) -> None:
    _job(default_org)

    body = Client().get("/job-status").content.decode()

    assert "APP-42" in body
    assert "billing-api" in body


def test_they_sit_between_the_organization_and_the_submitted_time(default_org: Org) -> None:
    """Column order is the request, not an accident.

    Asserted on the header row's positions rather than mere presence — a column added at the
    end would satisfy "it shows the application" and still be wrong.
    """
    import re

    _job(default_org)

    body = Client().get("/job-status").content.decode()
    headers = re.findall(r"<th[^>]*>(?:\s*<a[^>]*>)?\s*([A-Za-z ]+?)\s*(?:</a>)?\s*</th>", body)
    order = [h for h in headers if h in {"Organization", "Application", "Component", "Submitted"}]

    assert order == ["Organization", "Application", "Component", "Submitted"], headers


# --- Reviewing the manifest ---------------------------------------------------------------------


def test_the_manifest_cell_links_to_the_uploaded_file(default_org: Org) -> None:
    job = _job(default_org)

    body = Client().get("/job-status").content.decode()

    assert f"/job-status/manifest/{job.task_id}" in body


def test_the_manifest_page_shows_what_was_uploaded(default_org: Org) -> None:
    job = _job(default_org)

    body = Client().get(f"/job-status/manifest/{job.task_id}").content.decode()

    assert "django==5.2.1" in body
    assert "requests==2.32.3" in body
    assert "requirements.txt" in body, "the original filename should be shown"


def test_the_manifest_page_names_the_job_it_belongs_to(default_org: Org) -> None:
    """Arriving from a row, the reader needs to know they landed on the right one."""
    job = _job(default_org, application="APP-9", component="ledger")

    body = Client().get(f"/job-status/manifest/{job.task_id}").content.decode()

    assert "APP-9" in body
    assert "ledger" in body


def test_an_unknown_job_is_a_404(default_org: Org) -> None:
    assert Client().get("/job-status/manifest/00000000-0000-0000-0000-000000000000").status_code == 404


def test_another_orgs_manifest_is_readable(default_org: Org) -> None:
    """Consistent with Story 22.16: the pages list every org's jobs, so their rows must open."""
    other = Org.objects.create(name="Other", slug="other")
    job = _job(other)

    assert Client().get(f"/job-status/manifest/{job.task_id}").status_code == 200


# --- It is user-uploaded content ------------------------------------------------------------------


def test_manifest_content_is_escaped_not_executed(default_org: Org) -> None:
    """A manifest is whatever someone uploaded, so it must not be able to inject markup.

    Rendered into a page rather than served raw precisely so the template escapes it — a raw
    response would let the upload choose how the browser treats it.
    """
    job = _job(default_org, body=b"<script>alert('xss')</script>\n")

    body = Client().get(f"/job-status/manifest/{job.task_id}").content.decode()

    assert "<script>alert" not in body
    assert "&lt;script&gt;alert" in body


def test_a_huge_manifest_is_not_inlined(default_org: Org) -> None:
    """The upload cap is 50 MB; a `<pre>` that size would make the page unusable."""
    from inventory.sbom.pages import MANIFEST_INLINE_MAX_BYTES

    job = _job(default_org, body=b"x" * (MANIFEST_INLINE_MAX_BYTES + 1))

    body = Client().get(f"/job-status/manifest/{job.task_id}").content.decode()

    assert "too large" in body.lower()
    assert "x" * 1000 not in body


def test_a_manifest_whose_blob_is_gone_says_so(default_org: Org) -> None:
    """Artifact purging leaves the row; the file may be absent on disk (FR-8.1)."""
    job = _job(default_org)
    job.manifest.file.delete(save=True)

    response = Client().get(f"/job-status/manifest/{job.task_id}")

    assert response.status_code == 200
    assert "no longer available" in response.content.decode().lower()
