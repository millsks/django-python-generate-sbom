"""Story 21.15: the Licenses tab.

The assertion the Dev Notes single out: tier order must come from the **report**, not from a
list in the template. A hardcoded order renders correctly today and silently wrongly the day
the backend classifier changes, with nothing to catch it — so the ordering test derives its
expectation from the payload it fed in.
"""

from __future__ import annotations

import json

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client

from inventory.analysis.models import AnalysisReport
from inventory.analysis.services.license import TIER_ORDER
from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org
from inventory.users.services import create_org, register_user

PASSWORD = "pw12345678"

#: The tier element's opening tag. Matched in full because the tab's inline script mentions
#: both `<details>` and `[data-license-tier]` in comments and selectors.
TIER_TAG = '<details class="border rounded mb-2" data-license-tier'


def _report(*, empty_weak: bool = True) -> dict:
    """A report in the backend's own tier order, with one empty tier."""
    return {
        "tiers": [
            {"tier": "Strong Copyleft", "packages": [{"name": "gplpkg", "version": "1.0", "license": "GPL-3.0"}]},
            {
                "tier": "Weak Copyleft",
                "packages": [] if empty_weak else [{"name": "lgplpkg", "version": "2.0", "license": "LGPL-3.0"}],
            },
            {"tier": "Unknown", "packages": [{"name": "mysterypkg", "version": "3.0", "license": "UNKNOWN"}]},
            {"tier": "Permissive", "packages": [{"name": "mitpkg", "version": "4.0", "license": "MIT"}]},
        ],
        "summary": {"Strong Copyleft": 1, "Weak Copyleft": 0, "Unknown": 1, "Permissive": 1},
    }


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


def _job(
    org: Org, *, report: dict | None = None, failed: bool = False, reason: str | None = None, no_report: bool = False
) -> SBOMJob:
    upload = ManifestUpload.objects.create(
        org=org,
        file="m/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
        application_id="APP",
        component_name="c",
        repository_url="https://example.com/r",
        source_branch="main",
    )
    job = SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        result_key="sboms/x.json",
        summary_stats={"total_packages": 3},
    )
    if no_report:
        return job
    artifact_key = None
    if not failed:
        artifact_key = f"reports/{job.task_id}-license.json"
        default_storage.save(artifact_key, ContentFile(json.dumps(report if report is not None else _report())))
    AnalysisReport.objects.create(
        job=job,
        report_type=AnalysisReport.ReportType.LICENSE,
        artifact_key=artifact_key,
        failed=failed,
        failure_reason=reason,
    )
    return job


@pytest.fixture
def org_client():  # type: ignore[no-untyped-def]
    user = register_user(email="dev@example.com", password=PASSWORD)
    org = create_org(name="Acme", admin_user=user)
    return _client("dev@example.com"), org


def _tab(client: Client, job: SBOMJob) -> str:
    response = client.get(f"/results/{job.task_id}/tab/licenses")
    assert response.status_code == 200
    return response.content.decode()


# --- AC #1: four tiers, in the report's order ---------------------------------------------


@pytest.mark.django_db
def test_the_tiers_render_in_the_order_the_report_supplies(org_client) -> None:  # type: ignore[no-untyped-def]
    """Derived from the payload, not a hardcoded list — that is the whole point."""
    client, org = org_client
    report = _report()
    job = _job(org, report=report)

    html = _tab(client, job)

    expected = [tier["tier"] for tier in report["tiers"]]
    positions = [html.index(name) for name in expected]
    assert positions == sorted(positions), f"tiers not in the report's order: {expected}"


@pytest.mark.django_db
def test_a_reordered_report_renders_reordered(org_client) -> None:  # type: ignore[no-untyped-def]
    """The test that a hardcoded template order would fail.

    Feeding the tiers in a different order must change the rendering. If the template named
    the tiers itself, this would still render in the old order and pass the previous test.
    """
    client, org = org_client
    report = _report()
    report["tiers"].reverse()
    job = _job(org, report=report)

    html = _tab(client, job)

    assert html.index("Permissive") < html.index("Strong Copyleft")


def test_the_backend_owns_the_descending_attention_order() -> None:
    # Pins the classifier's order so a change there is a deliberate edit, not a silent one.
    assert TIER_ORDER == ["Strong Copyleft", "Weak Copyleft", "Unknown", "Permissive"]


@pytest.mark.django_db
def test_each_tier_shows_its_count_and_members(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    for package in ("gplpkg", "mysterypkg", "mitpkg"):
        assert package in html
    assert "GPL-3.0" in html
    assert "3 package(s) classified" in html


@pytest.mark.django_db
def test_packages_appear_under_their_own_tier(org_client) -> None:  # type: ignore[no-untyped-def]
    # Membership, not just presence: a package must sit between its tier heading and the next.
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert html.index("Strong Copyleft") < html.index("gplpkg") < html.index("Weak Copyleft")
    assert html.index("Unknown") < html.index("mysterypkg") < html.index("Permissive")


# --- AC #2: empty tiers start collapsed ---------------------------------------------------


@pytest.mark.django_db
def test_an_empty_tier_starts_collapsed_and_a_populated_one_open(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    # Matched on the full opening tag: the tab's inline script mentions <details> and the
    # [data-license-tier] selector in comments, so a bare substring count picks those up too.
    assert html.count(TIER_TAG) == 4
    # Three tiers have packages and carry `open`; the empty Weak Copyleft tier does not.
    assert html.count("open>") == 3


@pytest.mark.django_db
def test_a_populated_weak_tier_is_open_too(org_client) -> None:  # type: ignore[no-untyped-def]
    # Guards against the previous test passing because of a coincidence in tier position.
    client, org = org_client
    job = _job(org, report=_report(empty_weak=False))

    html = _tab(client, job)

    assert html.count("open>") == 4
    assert html.count(TIER_TAG) == 4
    assert "lgplpkg" in html


@pytest.mark.django_db
def test_an_empty_tier_still_renders_with_a_zero_count(org_client) -> None:  # type: ignore[no-untyped-def]
    # Collapsed, not hidden: the tier being empty is itself information.
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert "Weak Copyleft" in html
    assert "No packages in this tier." in html


# --- AC #3: expand / collapse all ---------------------------------------------------------


@pytest.mark.django_db
def test_expand_and_collapse_all_controls_are_present(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert 'data-license-toggle="open"' in html
    assert 'data-license-toggle="close"' in html
    # Every tier is addressable by the bulk control, including the collapsed one.
    assert html.count(TIER_TAG) == 4
    assert "[data-license-tier]" in html  # the selector the bulk buttons use


@pytest.mark.django_db
def test_the_per_tier_toggle_needs_no_javascript(org_client) -> None:  # type: ignore[no-untyped-def]
    """Native <details> is why this tab works with JS disabled apart from the bulk buttons."""
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert "<details" in html and "<summary" in html


# --- AC #4: the shared failure notice ------------------------------------------------------


@pytest.mark.django_db
def test_a_failed_phase_shows_the_shared_notice_with_its_reason(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, failed=True, reason="pypi_unavailable")

    html = _tab(client, job)

    assert "could not be generated" in html
    assert "pypi_unavailable" in html
    assert "remain available" in html


@pytest.mark.django_db
def test_the_failure_notice_is_the_one_story_21_14_built(org_client) -> None:  # type: ignore[no-untyped-def]
    """Reused, not copied — the Dev Notes asked for exactly this."""
    client, org = org_client
    licenses = _tab(client, _job(org, failed=True, reason="same_reason"))

    vuln_job = _job(org, no_report=True)
    AnalysisReport.objects.create(
        job=vuln_job, report_type=AnalysisReport.ReportType.VULN, failed=True, failure_reason="same_reason"
    )
    vulnerabilities = client.get(f"/results/{vuln_job.task_id}/tab/vulnerabilities").content.decode()

    notice = "This report could not be generated"
    assert notice in licenses and notice in vulnerabilities


@pytest.mark.django_db
def test_a_missing_report_is_distinct_from_a_failed_one(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client

    missing = _tab(client, _job(org, no_report=True))
    failed = _tab(client, _job(org, failed=True, reason="boom"))

    assert "No licence report is available" in missing
    assert missing != failed


# --- Access ---------------------------------------------------------------------------------


@pytest.mark.django_db
def test_another_orgs_tab_is_reachable(org_client) -> None:  # type: ignore[no-untyped-def]
    """Story 22.16: the pages are cross-org, so another org's tab must render.

    Was `test_the_tab_is_org_scoped`, asserting a 404. History now lists every org's jobs, so
    refusing to open their tabs would strand the rows it shows.
    """
    client, _ = org_client
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org)

    assert client.get(f"/results/{theirs.task_id}/tab/licenses").status_code == 200


@pytest.mark.django_db
def test_the_shell_renders_the_tab_server_side(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}?tab=licenses").content.decode()

    assert "Strong Copyleft" in html
    assert "gplpkg" in html
