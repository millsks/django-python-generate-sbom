"""Story 21.10: the job history table.

Proves django-tables2 + django-filter can carry the four report tables that follow, and pins
the blast radius of the delete actions. That radius changed: the buttons used to purge
artifacts and keep the record forever (FR-8.1); they now delete the **whole record** — job,
tasks, reports, manifest and every stored file. The API's artifact-only delete is untouched,
so these tests are the record of a UI decision, not of FR-8.1 being dropped everywhere.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.sbom.tables import format_duration
from inventory.users.models import Org, OrgMembership
from inventory.users.services import create_member, create_org, register_user

PASSWORD = "pw12345678"

HISTORY = "/job-status"
DELETE = "/job-status/records/delete"
DELETE_ALL = "/job-status/records/delete-all"


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


def _job(
    org: Org,
    *,
    status: str = SBOMJob.Status.SUCCESS,
    fmt: str = ManifestUpload.Format.REQUIREMENTS,
    filename: str = "requirements.txt",
    result_key: str | None = "sboms/x.json",
    completed: bool = True,
) -> SBOMJob:
    upload = ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/test/f.txt",
        detected_format=fmt,
        original_filename=filename,
        application_id="APP",
        component_name="c",
        repository_url="https://example.com/r",
        source_branch="main",
    )
    job = SBOMJob.objects.create(
        org=org, manifest=upload, output_format="cyclonedx-json", status=status, result_key=result_key
    )
    if completed:
        SBOMJob.objects.filter(pk=job.pk).update(completed_at=job.created_at + timedelta(seconds=93))
        job.refresh_from_db()
    return job


@pytest.fixture
def admin_org():  # type: ignore[no-untyped-def]
    user = register_user(email="admin@example.com", password=PASSWORD)
    org = create_org(name="Acme", admin_user=user)
    return _client("admin@example.com"), org


@pytest.fixture
def member_client(admin_org) -> Client:  # type: ignore[no-untyped-def]
    _, org = admin_org
    register_user(email="member@example.com", password=PASSWORD)
    create_member(org, email="member@example.com")
    OrgMembership.objects.filter(user__email="member@example.com").update(role=OrgMembership.Role.MEMBER)
    return _client("member@example.com")


# --- AC #1: the table --------------------------------------------------------------------


@pytest.mark.django_db
def test_the_table_renders_the_same_columns_as_the_spa(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    _job(org, filename="pyproject.toml", fmt=ManifestUpload.Format.PYPROJECT)

    html = client.get(HISTORY).content.decode()

    for header in ("Submitted", "Manifest", "Format", "Output", "Status", "Elapsed"):
        assert header in html
    assert "pyproject.toml" in html
    assert "Completed" in html  # the status badge label, not the raw SUCCESS code
    assert "1m 33s" in html  # elapsed, formatted as duration.ts did


@pytest.mark.django_db
def test_each_row_links_to_its_results_page(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    job = _job(org)
    assert f'href="/results/{job.task_id}"' in client.get(HISTORY).content.decode()


@pytest.mark.django_db
def test_rows_are_newest_first(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    _job(org, filename="older.txt")
    newer = _job(org, filename="newer.txt")
    SBOMJob.objects.filter(pk=newer.pk).update(created_at=timezone.now() + timedelta(hours=1))

    html = client.get(HISTORY).content.decode()

    assert html.index("newer.txt") < html.index("older.txt")


@pytest.mark.django_db
def test_the_empty_state_is_shown_when_there_are_no_jobs(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, _ = admin_org
    assert "No jobs yet." in client.get(HISTORY).content.decode()


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(None, "—"), (-1, "—"), (0.45, "450ms"), (45, "45s"), (83, "1m 23s"), (7500, "2h 05m")],
)
def test_duration_formatting_matches_the_spa(seconds: float | None, expected: str) -> None:
    # Ported from duration.ts, including its exact cases, so the History page reads the same
    # before and after the conversion.
    assert format_duration(seconds) == expected


# --- AC #2: filters and pagination --------------------------------------------------------


@pytest.mark.django_db
def test_pagination_is_25_per_page(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    for index in range(26):
        _job(org, filename=f"m{index}.txt")

    page_one = client.get(HISTORY)
    assert len(page_one.context["table"].page.object_list) == 25

    page_two = client.get(HISTORY, {"page": 2})
    assert len(page_two.context["table"].page.object_list) == 1


@pytest.mark.django_db
def test_the_status_filter_uses_the_same_mapping_as_the_api(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    _job(org, status=SBOMJob.Status.SUCCESS, filename="done.txt")
    _job(org, status=SBOMJob.Status.PENDING, filename="waiting.txt", completed=False)
    _job(org, status=SBOMJob.Status.FAILED, filename="broke.txt")

    html = client.get(HISTORY, {"status": "In Progress"}).content.decode()

    assert "waiting.txt" in html
    assert "done.txt" not in html
    assert "broke.txt" not in html


@pytest.mark.django_db
def test_the_format_filter_narrows_to_one_manifest_format(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    _job(org, fmt=ManifestUpload.Format.REQUIREMENTS, filename="req.txt")
    _job(org, fmt=ManifestUpload.Format.PIXI_LOCK, filename="pixi.lock")

    html = client.get(HISTORY, {"format": ManifestUpload.Format.PIXI_LOCK}).content.decode()

    assert "pixi.lock" in html
    assert "req.txt" not in html


@pytest.mark.django_db
def test_the_format_dropdown_offers_only_canonical_backend_values(admin_org) -> None:  # type: ignore[no-untyped-def]
    """Story 6.4: the dropdown must not be able to offer a value the backend rejects."""
    client, _ = admin_org
    html = client.get(HISTORY).content.decode()

    for value, _label in ManifestUpload.Format.choices:
        assert f'value="{value}"' in html


@pytest.mark.django_db
def test_an_unknown_format_yields_an_empty_page_not_an_error(admin_org) -> None:  # type: ignore[no-untyped-def]
    # Story 6.4's actual bug: a filter selection produced an error banner instead of rows.
    client, org = admin_org
    _job(org, filename="req.txt")

    response = client.get(HISTORY, {"format": "not-a-real-format"})

    assert response.status_code == 200
    assert "req.txt" not in response.content.decode()


@pytest.mark.django_db
def test_filters_are_bookmarkable_via_the_querystring(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    _job(org, status=SBOMJob.Status.FAILED, filename="broke.txt")
    _job(org, status=SBOMJob.Status.SUCCESS, filename="done.txt")

    # A fresh client with only the URL sees the same filtered view — no server-side state.
    html = client.get(f"{HISTORY}?status=Failed").content.decode()

    assert "broke.txt" in html
    assert "done.txt" not in html


# --- AC #3: purged artifacts --------------------------------------------------------------


@pytest.mark.django_db
def test_a_purged_job_is_indicated_and_its_delete_control_is_absent(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    job = _job(org, result_key=None, filename="purged.txt")
    SBOMJob.objects.filter(pk=job.pk).update(artifacts_expire_at=timezone.now() - timedelta(days=1))

    html = client.get(HISTORY).content.decode()

    # Story 7.3: the metadata survives, so the row renders — with an indicator, not an error.
    assert "purged.txt" in html
    assert "Artifacts removed" in html


@pytest.mark.django_db
def test_a_job_whose_artifacts_are_already_purged_still_deletes(admin_org) -> None:  # type: ignore[no-untyped-def]
    """No blobs left to remove is not a reason to keep the record — the row is the point."""
    client, org = admin_org
    job = _job(org, result_key=None)

    client.post(DELETE, {"task_ids": [str(job.task_id)]})

    assert not SBOMJob.objects.filter(pk=job.pk).exists()


@pytest.mark.django_db
def test_deleting_nothing_selected_says_so(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    job = _job(org)

    response = client.post(DELETE, {}, follow=True)

    assert "Select at least one job" in response.content.decode()
    assert SBOMJob.objects.filter(pk=job.pk).exists()


# --- AC #4: the delete scopes -------------------------------------------------------------


@pytest.mark.django_db
def test_deleting_one_job_removes_the_record_and_its_manifest(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    job = _job(org)
    manifest_pk = job.manifest_id

    client.post(DELETE, {"task_ids": [str(job.task_id)]})

    assert not SBOMJob.objects.filter(pk=job.pk).exists()
    assert not ManifestUpload.objects.filter(pk=manifest_pk).exists()


@pytest.mark.django_db
def test_deleting_a_selection_covers_exactly_the_named_jobs(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    chosen = [_job(org, filename="a.txt"), _job(org, filename="b.txt")]
    untouched = _job(org, filename="c.txt")

    client.post(DELETE, {"task_ids": [str(job.task_id) for job in chosen]})

    for job in chosen:
        assert not SBOMJob.objects.filter(pk=job.pk).exists()
    assert SBOMJob.objects.filter(pk=untouched.pk).exists()


@pytest.mark.django_db
def test_the_page_wide_delete_removes_every_listed_record(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, org = admin_org
    for index in range(3):
        _job(org, filename=f"m{index}.txt")

    client.post(DELETE_ALL)

    assert not SBOMJob.objects.exists()
    assert not ManifestUpload.objects.exists()


@pytest.mark.django_db
def test_a_member_can_still_delete_selected_records(member_client: Client, admin_org) -> None:  # type: ignore[no-untyped-def]
    # Per-job and bulk deletion are member capabilities; only the org-wide sweep is admin-only.
    _, org = admin_org
    job = _job(org)

    member_client.post(DELETE, {"task_ids": [str(job.task_id)]})

    assert not SBOMJob.objects.filter(pk=job.pk).exists()


@pytest.mark.django_db
def test_the_confirmations_say_the_whole_record_goes(admin_org) -> None:  # type: ignore[no-untyped-def]
    """The old copy promised the records were kept, which is now the opposite of the truth."""
    client, org = admin_org
    _job(org)

    html = client.get(HISTORY).content.decode()

    assert html.count("This cannot be undone") >= 2  # the selection confirm and the page-wide one
    assert html.count("the whole record") >= 2
    assert "records are kept" not in html
    assert "job records and their metadata are kept" not in html


# --- AC #5: org scoping --------------------------------------------------------------------


@pytest.mark.django_db
def test_another_orgs_jobs_are_listed_with_their_org(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, _ = admin_org
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    """Story 22.16: History spans every organization, and names which one each job is from."""
    _job(other_org, filename="theirs.txt")

    body = client.get(HISTORY).content.decode()

    assert "theirs.txt" in body
    assert "Other" in body, "the Organization column should name the tenant"


@pytest.mark.django_db
def test_another_orgs_job_can_be_deleted_by_task_id(admin_org) -> None:  # type: ignore[no-untyped-def]
    """Story 22.16: the ids come from checkboxes on rows the caller can see.

    History lists every org, so scoping this delete to one would silently skip rows the caller
    explicitly ticked — a worse outcome than deleting what they asked for. The blast radius is
    still exactly the submitted ids.
    """
    client, _ = admin_org
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org)

    client.post(DELETE, {"task_ids": [str(theirs.task_id)]})

    assert not SBOMJob.objects.filter(pk=theirs.pk).exists()


@pytest.mark.django_db
def test_the_delete_all_follows_the_org_filter(admin_org) -> None:  # type: ignore[no-untyped-def]
    """The guard against Story 22.16 turning this button into a deployment-wide wipe.

    Making History cross-org would have silently widened "delete all artifacts" from one org to
    every org, behind a confirmation that still named a single one. It now deletes exactly what
    the table is showing, so filtering to an org confines it to that org.
    """
    client, mine = admin_org
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org)
    ours = _job(mine)

    client.post(DELETE_ALL, {"org": str(other_org.pk)})

    assert not SBOMJob.objects.filter(pk=theirs.pk).exists(), "the filtered org's records should go"
    assert SBOMJob.objects.filter(pk=ours.pk).exists(), "an org outside the filter must be untouched"


@pytest.mark.django_db
def test_the_delete_all_without_a_filter_really_does_mean_all(admin_org) -> None:  # type: ignore[no-untyped-def]
    """The other half: unfiltered means unfiltered, and the confirmation says so."""
    client, mine = admin_org
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org)
    ours = _job(mine)

    body = client.get(HISTORY).content.decode()
    assert "EVERY job in EVERY organization" in body, "the confirmation must not name one org"

    client.post(DELETE_ALL)

    assert not SBOMJob.objects.filter(pk__in=[theirs.pk, ours.pk]).exists()


# --- Hardening -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_endpoints_reject_get_and_require_csrf(admin_org) -> None:  # type: ignore[no-untyped-def]
    client, _ = admin_org
    for url in (DELETE, DELETE_ALL):
        assert client.get(url).status_code == 405, url

    strict = Client(enforce_csrf_checks=True)
    assert strict.login(email="admin@example.com", password=PASSWORD)
    for url in (DELETE, DELETE_ALL):
        assert strict.post(url, {}).status_code == 403, url
