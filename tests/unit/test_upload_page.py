"""Story 21.9: the manifest upload and job submission page.

The primary user journey, and the first server-rendered page that starts real work. The
tests that matter most are the ones proving the page did **not** re-implement anything:
the concurrency gate, the initial status write, and deferred dispatch all belong to
`sbom.services.submit_job`, which the DRF endpoint shares.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.sbom.services import OUTPUT_FORMAT_CHOICES, OUTPUT_FORMAT_MAP
from inventory.users.models import OrgMembership
from inventory.users.services import create_member, create_org, register_user

PASSWORD = "pw12345678"
UPLOAD = "/upload"

# Patch the task at its canonical home: submit_job imports it lazily to avoid a circular
# import, so a name on the view or service module would not be the object actually called.
DISPATCH = "inventory.tasks.sbom_pipeline.run_sbom_pipeline.delay_on_commit"

REQUIREMENTS = b"requests==2.32.3\nstructlog==24.4.0\n"


def _manifest(name: str = "requirements.txt", content: bytes = REQUIREMENTS) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="text/plain")


def _payload(org: object, **overrides: object) -> dict[str, object]:
    """Build a valid POST body.

    ``org`` is required because Story 21.24 added an explicit organization field: with the
    login removed there is no "active org" to infer, so the choice is made on the form.
    """
    data: dict[str, object] = {
        "org": getattr(org, "pk", org),
        "file": _manifest(),
        "application_id": "APP-42",
        "component_name": "billing-service",
        "repository_url": "https://example.com/org/repo",
        "source_branch": "main",
        "output_format": "cdx-json",
    }
    data.update(overrides)
    return data


@pytest.fixture
def member_client():  # type: ignore[no-untyped-def]
    """A member of an org, able to submit."""
    user = register_user(email="dev@example.com", password=PASSWORD)
    org = create_org(name="Acme", admin_user=user)
    client = Client()
    assert client.login(email="dev@example.com", password=PASSWORD)
    return client, org


# --- AC #1/#2: the form ------------------------------------------------------------------


@pytest.mark.django_db
def test_the_form_renders_multipart_with_all_five_fields(member_client) -> None:  # type: ignore[no-untyped-def]
    client, _org = member_client
    html = client.get(UPLOAD).content.decode()

    assert 'enctype="multipart/form-data"' in html
    for field in ("org", "file", "application_id", "component_name", "repository_url", "source_branch"):
        assert f'name="{field}"' in html
    # Story 10.x parity: the branch defaults to main.
    assert 'value="main"' in html


@pytest.mark.django_db
def test_the_format_choices_come_from_the_backend(member_client) -> None:  # type: ignore[no-untyped-def]
    """Story 6.4's lesson: a hand-kept copy of a choice list is what caused that bug."""
    client, _org = member_client
    html = client.get(UPLOAD).content.decode()

    for value, label in OUTPUT_FORMAT_CHOICES:
        assert f'value="{value}"' in html
        assert label in html


def test_output_format_choices_cover_every_supported_format() -> None:
    # If a format is added to OUTPUT_FORMAT_MAP without a label, this fails rather than the
    # form silently offering fewer options than the API accepts.
    assert [value for value, _label in OUTPUT_FORMAT_CHOICES] == list(OUTPUT_FORMAT_MAP)


@pytest.mark.django_db
def test_every_provenance_field_is_required(member_client) -> None:  # type: ignore[no-untyped-def]
    client, _org = member_client

    response = client.post(UPLOAD, {"file": _manifest()})

    assert response.status_code == 200
    assert SBOMJob.objects.count() == 0
    body = response.content.decode()
    assert body.count("This field is required.") >= 4


# --- AC #4/#5: a successful submission ----------------------------------------------------


@pytest.mark.django_db
def test_a_valid_upload_creates_a_pending_job_and_redirects(member_client) -> None:  # type: ignore[no-untyped-def]
    client, org = member_client

    with patch(DISPATCH) as dispatch:
        response = client.post(UPLOAD, _payload(org))

    job = SBOMJob.objects.get()
    # AC #12: the initial PENDING write is the view/service's sole permitted status write.
    assert job.status == SBOMJob.Status.PENDING
    assert job.org == org
    assert job.user is not None and job.user.email == "dev@example.com"

    # AC #10: dispatch is deferred to commit, so a worker cannot see an uncommitted job row.
    dispatch.assert_called_once_with(str(job.task_id))

    # AC #4: POST-redirect-GET, so a refresh cannot enqueue a second job.
    assert response.status_code == 302
    assert response.headers["Location"] == f"/results/{job.task_id}"


@pytest.mark.django_db
def test_the_manifest_is_stored_with_its_provenance(member_client) -> None:  # type: ignore[no-untyped-def]
    client, org = member_client

    with patch(DISPATCH):
        client.post(UPLOAD, _payload(org))

    upload = ManifestUpload.objects.get()
    assert upload.org == org
    assert upload.application_id == "APP-42"
    assert upload.component_name == "billing-service"
    assert upload.repository_url == "https://example.com/org/repo"
    assert upload.source_branch == "main"
    assert upload.detected_format == ManifestUpload.Format.REQUIREMENTS


@pytest.mark.django_db
def test_the_selected_output_format_is_mapped_to_the_internal_id(member_client) -> None:  # type: ignore[no-untyped-def]
    client, org = member_client

    with patch(DISPATCH):
        client.post(UPLOAD, _payload(org, output_format="spdx-2.3"))

    assert SBOMJob.objects.get().output_format == OUTPUT_FORMAT_MAP["spdx-2.3"]


# --- AC #3: every rejection is a form error, and creates nothing ---------------------------


@pytest.mark.django_db
def test_an_unrecognised_manifest_is_a_field_error(member_client) -> None:  # type: ignore[no-untyped-def]
    client, org = member_client

    with patch(DISPATCH) as dispatch:
        response = client.post(UPLOAD, _payload(org, file=_manifest("notes.txt", b"this is not a manifest\n")))

    assert response.status_code == 200
    assert SBOMJob.objects.count() == 0
    assert ManifestUpload.objects.count() == 0
    dispatch.assert_not_called()


@pytest.mark.django_db
def test_an_oversize_file_is_rejected_without_touching_storage(member_client) -> None:  # type: ignore[no-untyped-def]
    """FR-3.4. The form applies the same cap as the API, read from the same constant.

    The cap is lowered for the test rather than allocating 50 MB. Setting `.size` on a
    SimpleUploadedFile does **not** work: the test client serialises the upload and Django
    rebuilds the UploadedFile server-side, so a faked size is discarded and the real (tiny)
    length is what the validator sees — the check silently never fires.
    """
    client, org = member_client

    with patch("inventory.sbom.forms.MAX_MANIFEST_BYTES", 8), patch(DISPATCH) as dispatch:
        response = client.post(UPLOAD, _payload(org))

    assert response.status_code == 200
    assert "50 MB limit" in response.content.decode()
    assert SBOMJob.objects.count() == 0
    assert ManifestUpload.objects.count() == 0
    dispatch.assert_not_called()


@pytest.mark.django_db
def test_the_concurrency_gate_refuses_with_retry_guidance(member_client, settings) -> None:  # type: ignore[no-untyped-def]
    """AD-7, and the gate is the SERVICE's — the page must not have its own copy."""
    client, org = member_client
    settings.SBOM_MAX_CONCURRENT_JOBS_PER_ORG = 1
    with patch(DISPATCH):
        client.post(UPLOAD, _payload(org))
    assert SBOMJob.objects.count() == 1

    with patch(DISPATCH) as dispatch:
        response = client.post(UPLOAD, _payload(org))

    assert response.status_code == 200
    body = response.content.decode()
    assert "maximum number of jobs" in body
    assert "try again" in body.lower()  # the human form of Retry-After
    # No second job, and nothing dispatched.
    assert SBOMJob.objects.count() == 1
    dispatch.assert_not_called()


@pytest.mark.django_db
def test_a_malformed_repository_url_is_a_field_error(member_client) -> None:  # type: ignore[no-untyped-def]
    # URLField, matching the SPA's type="url" and the serializer.
    client, org = member_client

    response = client.post(UPLOAD, _payload(org, repository_url="not a url"))

    assert response.status_code == 200
    assert "Enter a valid URL." in response.content.decode()
    assert SBOMJob.objects.count() == 0


# --- AC #6: access ------------------------------------------------------------------------


@pytest.mark.django_db
def test_an_unknown_org_is_a_field_error_rather_than_a_job() -> None:
    """Was the zero-org denial, which Story 21.24 removed along with the access control.

    The organization is now chosen on the form, so the thing worth protecting is that the
    field cannot be hand-edited into filing a job against an org that does not exist.
    """
    register_user(email="nobody@example.com", password=PASSWORD)
    client = Client()
    assert client.login(email="nobody@example.com", password=PASSWORD)

    with patch(DISPATCH) as dispatch:
        response = client.post(UPLOAD, _payload(999999))

    assert response.status_code == 200  # re-rendered form, not a redirect
    assert SBOMJob.objects.count() == 0
    dispatch.assert_not_called()


@pytest.mark.django_db
def test_the_admin_org_is_not_offered_as_an_upload_target(member_client) -> None:  # type: ignore[no-untyped-def]
    """Story 2.12: the ADMIN org is a platform tier, never a workspace to file jobs into."""
    from inventory.users.models import Org

    client, _ = member_client
    admin_org = Org.objects.get(is_admin_org=True)

    html = client.get(UPLOAD).content.decode()

    assert f'value="{admin_org.pk}"' not in html


@pytest.mark.django_db
def test_submission_requires_a_csrf_token(member_client) -> None:  # type: ignore[no-untyped-def]
    _, org = member_client
    strict = Client(enforce_csrf_checks=True)
    assert strict.login(email="dev@example.com", password=PASSWORD)

    assert strict.post(UPLOAD, _payload(org)).status_code == 403
    assert SBOMJob.objects.count() == 0


@pytest.mark.django_db
def test_a_plain_member_can_submit(member_client) -> None:  # type: ignore[no-untyped-def]
    """Submitting is a member capability, not an admin one — the mixin is OrgMemberRequired."""
    _, org = member_client
    register_user(email="plain@example.com", password=PASSWORD)
    create_member(org, email="plain@example.com")
    OrgMembership.objects.filter(user__email="plain@example.com").update(role=OrgMembership.Role.MEMBER)
    client = Client()
    assert client.login(email="plain@example.com", password=PASSWORD)

    with patch(DISPATCH):
        response = client.post(UPLOAD, _payload(org))

    assert response.status_code == 302
    assert SBOMJob.objects.count() == 1
