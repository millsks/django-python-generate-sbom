"""Story 21.14: the Vulnerabilities tab.

The Dev Notes name the likeliest defect outright: there are **three distinct empty-ish
states** — clean scan, no data, failed phase — and conflating any two of them is the failure
mode. Each gets its own test asserting the rendered text differs, because all three look
alike as "no rows".
"""

from __future__ import annotations

import json

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client

from inventory.analysis.models import AnalysisReport
from inventory.analysis.tables import SEVERITY_RANK, vulnerability_rows
from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org
from inventory.users.services import create_org, register_user

PASSWORD = "pw12345678"

REPORT = {
    "packages": [
        {
            "name": "lowpkg",
            "version": "1.0.0",
            "vulnerabilities": [
                {
                    "id": "GHSA-low",
                    "aliases": ["CVE-2024-0001"],
                    "cve": "CVE-2024-0001",
                    "cvss_score": 2.1,
                    "severity": "Low",
                    "advisory_url": "https://osv.dev/GHSA-low",
                    "cwe": ["CWE-200"],
                }
            ],
        },
        {
            "name": "critpkg",
            "version": "2.0.0",
            "vulnerabilities": [
                {
                    "id": "GHSA-crit",
                    "aliases": [],
                    "cve": None,
                    "cvss_score": 9.8,
                    "severity": "Critical",
                    "advisory_url": "https://osv.dev/GHSA-crit",
                    "cwe": [],
                }
            ],
        },
    ],
    "summary": {"vulnerable_package_count": 2},
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
        summary_stats={"total_packages": 12},
    )
    if no_report:
        return job
    artifact_key = None
    if not failed:
        artifact_key = f"reports/{job.task_id}-vuln.json"
        default_storage.save(artifact_key, ContentFile(json.dumps(report if report is not None else REPORT)))
    AnalysisReport.objects.create(
        job=job,
        report_type=AnalysisReport.ReportType.VULN,
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


def _tab(client: Client, job: SBOMJob, **params: str) -> str:
    query = ("?" + "&".join(f"{k}={v}" for k, v in params.items())) if params else ""
    response = client.get(f"/results/{job.task_id}/tab/vulnerabilities{query}")
    assert response.status_code == 200
    return response.content.decode()


# --- AC #1/#2: the table -------------------------------------------------------------------


@pytest.mark.django_db
def test_the_table_renders_the_same_columns_as_the_spa(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    for header in ("Package", "Version", "CVE / GHSA", "CVSS", "Severity"):
        assert header in html
    assert "critpkg" in html and "lowpkg" in html


@pytest.mark.django_db
def test_the_default_sort_is_severity_descending(org_client) -> None:  # type: ignore[no-untyped-def]
    """Story 8.16's default. Critical must lead — the worst findings are the point of the tab."""
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert html.index("critpkg") < html.index("lowpkg")


def test_severity_sorts_by_danger_not_alphabetically() -> None:
    # Alphabetically "Critical" < "High" < "Low" < "Medium", which would bury the worst
    # findings. The rank is what prevents that, so it is asserted directly.
    assert SEVERITY_RANK["Critical"] > SEVERITY_RANK["High"] > SEVERITY_RANK["Medium"]
    assert SEVERITY_RANK["Medium"] > SEVERITY_RANK["Low"] > SEVERITY_RANK["Unknown"]


@pytest.mark.django_db
def test_sorting_is_carried_in_the_querystring(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    ascending = _tab(client, job, sort="severity")

    assert ascending.index("lowpkg") < ascending.index("critpkg")


@pytest.mark.django_db
def test_advisory_links_are_outbound_and_safe(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert "https://osv.dev/GHSA-crit" in html
    assert 'rel="noopener noreferrer"' in html


@pytest.mark.django_db
def test_identifiers_merge_the_osv_id_and_its_aliases(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert "GHSA-low, CVE-2024-0001" in html


def test_identifier_merging_de_duplicates() -> None:
    # The SPA used a Set; a duplicated alias must not appear twice.
    rows = vulnerability_rows(
        {
            "packages": [
                {
                    "name": "p",
                    "version": "1",
                    "vulnerabilities": [{"id": "CVE-1", "aliases": ["CVE-1", "GHSA-x"], "severity": "Low"}],
                }
            ]
        }
    )
    assert rows[0]["ids"] == "CVE-1, GHSA-x"


@pytest.mark.django_db
def test_the_cwe_enrichment_from_epic_4_is_shown(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)
    assert "CWE-200" in _tab(client, job)


@pytest.mark.django_db
def test_one_row_per_finding_not_per_package(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    report = {
        "packages": [
            {
                "name": "multi",
                "version": "1.0",
                "vulnerabilities": [
                    {"id": "A", "aliases": [], "severity": "High", "advisory_url": "https://osv.dev/A"},
                    {"id": "B", "aliases": [], "severity": "Low", "advisory_url": "https://osv.dev/B"},
                ],
            }
        ],
        "summary": {"vulnerable_package_count": 1},
    }
    job = _job(org, report=report)

    html = _tab(client, job)

    assert "2 finding(s)" in html


# --- Severity filtering --------------------------------------------------------------------


@pytest.mark.django_db
def test_the_severity_filter_narrows_the_table(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job, severity="Critical")

    assert "critpkg" in html
    assert "lowpkg" not in html


@pytest.mark.django_db
def test_the_severity_filter_survives_a_refresh_via_the_querystring(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    first = _tab(client, job, severity="Critical")
    second = _tab(client, job, severity="Critical")

    assert first == second
    assert "lowpkg" not in second


@pytest.mark.django_db
def test_the_filter_form_keeps_the_active_tab(org_client) -> None:  # type: ignore[no-untyped-def]
    # Without this the filter submit would bounce the user back to Overview.
    client, org = org_client
    job = _job(org)
    assert 'name="tab" value="vulnerabilities"' in _tab(client, job)


@pytest.mark.django_db
def test_an_unknown_severity_shows_nothing_rather_than_everything(org_client) -> None:  # type: ignore[no-untyped-def]
    """A stale link must not misrepresent a filtered view as the complete set."""
    client, org = org_client
    job = _job(org)

    html = _tab(client, job, severity="Bogus")

    assert "critpkg" not in html
    assert "lowpkg" not in html


# --- The three empty-ish states, kept distinct ---------------------------------------------


@pytest.mark.django_db
def test_a_clean_scan_states_that_none_were_found(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, report={"packages": [], "summary": {"vulnerable_package_count": 0}})

    html = _tab(client, job)

    assert "No vulnerabilities found" in html
    assert "12 package(s)" in html  # concrete, from the job's own package count


@pytest.mark.django_db
def test_a_missing_report_says_no_report_is_available(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, no_report=True)

    html = _tab(client, job)

    assert "No vulnerability report is available" in html


@pytest.mark.django_db
def test_a_failed_phase_shows_the_shared_notice_with_its_reason(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, failed=True, reason="nvd_unavailable")

    html = _tab(client, job)

    assert "could not be generated" in html
    assert "nvd_unavailable" in html
    # The SPA's reassurance that one failed phase does not invalidate the rest.
    assert "remain available" in html


@pytest.mark.django_db
def test_the_three_states_are_visibly_different(org_client) -> None:  # type: ignore[no-untyped-def]
    """The Dev Notes' warning, asserted head-on: no two of these may read the same."""
    client, org = org_client

    clean = _tab(client, _job(org, report={"packages": [], "summary": {}}))
    missing = _tab(client, _job(org, no_report=True))
    failed = _tab(client, _job(org, failed=True, reason="boom"))

    bodies = {clean, missing, failed}
    assert len(bodies) == 3, "two empty-ish states render identically"


@pytest.mark.django_db
def test_a_failed_report_is_not_reported_as_merely_missing(org_client) -> None:  # type: ignore[no-untyped-def]
    # A failed row also has no artifact; checking `failed` first is what keeps the reason.
    client, org = org_client
    job = _job(org, failed=True, reason="rate_limited")

    html = _tab(client, job)

    assert "rate_limited" in html
    assert "No vulnerability report is available" not in html


# --- Access ---------------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_tab_is_org_scoped(org_client) -> None:  # type: ignore[no-untyped-def]
    client, _ = org_client
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org)

    assert client.get(f"/results/{theirs.task_id}/tab/vulnerabilities").status_code == 404


@pytest.mark.django_db
def test_the_shell_renders_the_tab_server_side(org_client) -> None:  # type: ignore[no-untyped-def]
    # ?tab=vulnerabilities must work on a cold load, not only via htmx.
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}?tab=vulnerabilities").content.decode()

    assert "critpkg" in html


@pytest.mark.django_db
def test_a_finding_with_no_advisory_url_renders_a_dash(org_client) -> None:  # type: ignore[no-untyped-def]
    """Regression: this crashed until Story 21.16 hit the same shape elsewhere.

    `render_advisory_url` returned `format_html("—")`, and format_html raises TypeError when
    given no arguments. Every fixture here happened to supply an advisory URL, so the branch
    was never taken — a latent 500 for any finding without one.
    """
    client, org = org_client
    report = {
        "packages": [
            {
                "name": "nolink",
                "version": "1.0",
                "vulnerabilities": [{"id": "GHSA-nolink", "aliases": [], "severity": "High", "advisory_url": None}],
            }
        ],
        "summary": {"vulnerable_package_count": 1},
    }
    job = _job(org, report=report)

    html = _tab(client, job)

    assert "nolink" in html
    assert "—" in html
