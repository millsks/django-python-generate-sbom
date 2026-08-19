"""Story 21.16: the Version Currency tab.

The story calls this the trickiest tab, and names why: an alphabetical sort on the currency
string produces `behind-1, behind-2+, current, unknown` — which *looks* sorted and buries the
most outdated packages in the middle. `test_status_sorts_by_class_rank_not_alphabetically`
asserts the exact rendered sequence, and is the load-bearing test in this module.
"""

from __future__ import annotations

import json
import re

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client

from inventory.analysis.models import AnalysisReport
from inventory.analysis.tables import CURRENCY_RANK, registry_url
from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org
from inventory.users.services import create_org, register_user

PASSWORD = "pw12345678"

# The seven columns, in the order Story 8.23 requires.
COLUMN_ORDER = ["Package", "Installed", "Status", "PyPI Latest", "conda-forge Latest", "LTS", "Source"]


def _headers(html: str) -> list[str]:
    """Extract the table's header labels in render order.

    Parsed rather than matched by substring: a sortable header is wrapped in an anchor while a
    non-sortable one is bare text with surrounding whitespace, so `">Label<"` finds some and
    misses others. Comparing the extracted list is also a stronger assertion than checking
    relative positions.
    """
    cells = re.findall(r"<th[^>]*>(.*?)</th>", html, re.S)
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cell)).strip() for cell in cells]


def _package(name: str, currency: str, **overrides: object) -> dict:
    package = {
        "name": name,
        "installed": "1.0.0",
        "latest": "2.0.0",
        "currency": currency,
        "lts": None,
        "on_lts": None,
        "ecosystem": "pypi",
        "conda_latest": "2.0.0",
        "latest_mismatch": False,
    }
    package.update(overrides)
    return package


#: One package per currency class, deliberately inserted in an order that is neither the rank
#: order nor alphabetical, so a passing sort test cannot be a coincidence of input order.
RANK_REPORT = {
    "packages": [
        _package("currentpkg", "current"),
        _package("unknownpkg", "unknown"),
        _package("behind2pkg", "behind-2+"),
        _package("behind1pkg", "behind-1"),
    ],
    "summary": {},
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
        summary_stats={"total_packages": 4},
    )
    if no_report:
        return job
    artifact_key = None
    if not failed:
        artifact_key = f"reports/{job.task_id}-version.json"
        default_storage.save(artifact_key, ContentFile(json.dumps(report if report is not None else RANK_REPORT)))
    AnalysisReport.objects.create(
        job=job,
        report_type=AnalysisReport.ReportType.VERSION,
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
    response = client.get(f"/results/{job.task_id}/tab/versions{query}")
    assert response.status_code == 200
    return response.content.decode()


# --- AC #3: the rank sort, the reason this tab is "trickiest" -----------------------------


@pytest.mark.django_db
def test_status_sorts_by_class_rank_not_alphabetically(org_client) -> None:  # type: ignore[no-untyped-def]
    """The load-bearing test.

    Alphabetically the classes order `behind-1, behind-2+, current, unknown`. By rank, sorted
    descending, they must be `behind-2+, behind-1, current, unknown` — most outdated first.
    The two agree on nothing except that `behind-1` precedes `behind-2+`, so asserting the
    exact sequence distinguishes them.
    """
    client, org = org_client
    job = _job(org)

    html = _tab(client, job, sort="-currency")

    order = [html.index(name) for name in ("behind2pkg", "behind1pkg", "currentpkg", "unknownpkg")]
    assert order == sorted(order), "status did not sort by rank — most outdated must lead"
    # And explicitly NOT the alphabetical order an unwary implementation produces.
    assert html.index("behind2pkg") < html.index("behind1pkg")


def test_the_rank_mapping_matches_the_spa() -> None:
    # VersionsTab.tsx:28. Pinned directly so a change to the mapping is deliberate.
    assert CURRENCY_RANK == {"behind-2+": 3, "behind-1": 2, "current": 1, "unknown": 0}


@pytest.mark.django_db
def test_ascending_status_puts_the_most_current_first(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job, sort="currency")

    assert html.index("unknownpkg") < html.index("currentpkg") < html.index("behind1pkg")


# --- AC #4: the default sort ---------------------------------------------------------------


@pytest.mark.django_db
def test_the_default_sort_is_package_name_ascending(org_client) -> None:  # type: ignore[no-untyped-def]
    """Story 8.16 / VersionsTab.tsx:100."""
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    names = ["behind1pkg", "behind2pkg", "currentpkg", "unknownpkg"]  # alphabetical
    positions = [html.index(name) for name in names]
    assert positions == sorted(positions)


# --- AC #1: seven columns, in order --------------------------------------------------------


@pytest.mark.django_db
def test_all_seven_columns_render_in_order(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert _headers(html) == COLUMN_ORDER


@pytest.mark.django_db
def test_pypi_latest_sits_immediately_before_conda_forge_latest(org_client) -> None:  # type: ignore[no-untyped-def]
    """Story 8.23 put them side by side on purpose, so they can be compared at a glance."""
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    headers = _headers(html)
    # Adjacent, not merely both present: Story 8.23 moved them together on purpose.
    assert headers.index("conda-forge Latest") == headers.index("PyPI Latest") + 1


# --- AC #2: registry links -----------------------------------------------------------------


@pytest.mark.django_db
def test_a_pypi_package_links_to_its_project_page(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert "https://pypi.org/project/currentpkg/1.0.0/" in html
    assert 'rel="noopener noreferrer"' in html


@pytest.mark.django_db
def test_a_conda_package_links_to_the_prefix_dev_explorer(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, report={"packages": [_package("condapkg", "current", ecosystem="conda")], "summary": {}})

    html = _tab(client, job)

    assert "https://prefix.dev/channels/conda-forge/packages/condapkg" in html


@pytest.mark.django_db
def test_an_unknown_ecosystem_renders_plain_text_with_no_anchor(org_client) -> None:  # type: ignore[no-untyped-def]
    """A guessed URL would 404; plain text is the honest rendering."""
    client, org = org_client
    job = _job(org, report={"packages": [_package("mysterypkg", "current", ecosystem=None)], "summary": {}})

    html = _tab(client, job)

    assert "mysterypkg" in html
    assert "pypi.org/project/mysterypkg" not in html
    assert "prefix.dev" not in html


def test_registry_urls_are_encoded() -> None:
    # A package name is data; it must not be able to break out of the URL.
    assert registry_url("weird name", None, "pypi") == "https://pypi.org/project/weird%20name/"
    assert registry_url("a/b", None, "conda") == "https://prefix.dev/channels/conda-forge/packages/a%2Fb"
    assert registry_url("anything", None, None) is None


# --- AC #5: divergence and the three LTS states --------------------------------------------


@pytest.mark.django_db
def test_a_diverging_conda_latest_is_flagged(org_client) -> None:  # type: ignore[no-untyped-def]
    """Story 8.10: the conda-forge latest differing from PyPI's is worth noticing."""
    client, org = org_client
    job = _job(
        org,
        report={
            "packages": [_package("divergent", "current", conda_latest="3.0.0", latest_mismatch=True)],
            "summary": {},
        },
    )

    html = _tab(client, job)

    assert "Differs from the PyPI latest" in html
    assert "text-danger" in html


@pytest.mark.django_db
def test_a_matching_conda_latest_is_not_flagged(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = _tab(client, job)

    assert "Differs from the PyPI latest" not in html


@pytest.mark.django_db
def test_the_three_lts_states_render_distinctly(org_client) -> None:  # type: ignore[no-untyped-def]
    """Story 8.7: no LTS tracked, on the LTS series, or targeting it."""
    client, org = org_client
    job = _job(
        org,
        report={
            "packages": [
                _package("nolts", "current", lts=None, on_lts=None),
                _package("onlts", "current", lts="3.2", on_lts=True),
                _package("targetlts", "current", lts="4.1", on_lts=False),
            ],
            "summary": {},
        },
    )

    html = _tab(client, job)

    assert "On LTS (3.2)" in html
    assert "LTS 4.1 (target)" in html
    # The no-LTS row renders a dash rather than an empty cell or a bogus chip.
    assert "On LTS (None)" not in html and "LTS None" not in html


# --- AC #6: the shared failure notice ------------------------------------------------------


@pytest.mark.django_db
def test_a_failed_phase_shows_the_shared_notice_with_its_reason(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, failed=True, reason="pypi_timeout")

    html = _tab(client, job)

    assert "could not be generated" in html
    assert "pypi_timeout" in html
    assert "remain available" in html


@pytest.mark.django_db
def test_missing_and_failed_stay_distinct(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client

    missing = _tab(client, _job(org, no_report=True))
    failed = _tab(client, _job(org, failed=True, reason="boom"))

    assert "No version-currency report is available" in missing
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

    assert client.get(f"/results/{theirs.task_id}/tab/versions").status_code == 200


@pytest.mark.django_db
def test_the_shell_renders_the_tab_server_side(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}?tab=versions").content.decode()

    assert "currentpkg" in html
    assert "conda-forge Latest" in html
