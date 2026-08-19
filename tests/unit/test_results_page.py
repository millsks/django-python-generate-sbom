"""Story 21.12: the results shell and Overview tab.

Two assertions carry the most weight: that the Overview reads **only** `summary_stats`
(NFR-2.2 — fetching four report artifacts to draw four cards is the cost that column exists
to avoid), and that a failed phase reads "Unavailable" rather than 0 (FR-6.7 — a zero would
claim something the system cannot know).
"""

from __future__ import annotations

import re

import pytest
from django.test import Client

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.sbom.overview import UNAVAILABLE, build_metrics
from inventory.sbom.pages import RESULT_TABS
from inventory.users.models import Org
from inventory.users.services import create_org, register_user

PASSWORD = "pw12345678"

# The SPA's tab order, written out independently of the implementation so a reordering has to
# be a deliberate edit in two places.
SPA_TAB_ORDER = ["Overview", "SBOM", "Vulnerabilities", "Licenses", "Version Currency"]

CSRF = re.compile(r'value="[A-Za-z0-9]{32,}"')

FULL_STATS = {
    "total_packages": 42,
    "reports": {
        "vuln": {"failed": False, "vulnerable_package_count": 3},
        "license": {"failed": False, "Permissive": 30, "Strong Copyleft": 2, "Weak Copyleft": 1, "Unknown": 9},
        "version": {"failed": False, "current": 20, "behind-1": 5, "behind-2+": 2, "unknown": 15},
    },
}


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


def _job(org: Org, *, status: str = SBOMJob.Status.SUCCESS, stats: dict | None = None, purged: bool = False):  # type: ignore[no-untyped-def]
    upload = ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
        application_id="APP-1",
        component_name="billing",
        repository_url="https://example.com/r",
        source_branch="main",
    )
    return SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=status,
        summary_stats=stats if stats is not None else FULL_STATS,
        result_key=None if purged or status != SBOMJob.Status.SUCCESS else "sboms/x.json",
    )


@pytest.fixture
def org_client():  # type: ignore[no-untyped-def]
    user = register_user(email="dev@example.com", password=PASSWORD)
    org = create_org(name="Acme", admin_user=user)
    return _client("dev@example.com"), org


# --- AC #1: the shell ---------------------------------------------------------------------


@pytest.mark.django_db
def test_the_five_tabs_render_in_the_spa_order(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}").content.decode()

    positions = [html.index(f">{label}<") for label in SPA_TAB_ORDER]
    assert positions == sorted(positions), "tabs are not in the SPA's order"


def test_the_tab_list_matches_the_spa_exactly() -> None:
    # The Dependency Graph tab was retired by Story 20.1 and SBOM inserted at index 1 by 8.6;
    # this pins the resulting order so neither change is silently undone.
    assert [label for _slug, label in RESULT_TABS] == SPA_TAB_ORDER


@pytest.mark.django_db
def test_the_active_tab_lives_in_the_url_and_survives_a_refresh(org_client) -> None:  # type: ignore[no-untyped-def]
    """A small improvement on the SPA, which held tab state in React and lost it on reload."""
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}?tab=licenses").content.decode()

    # Rendered server-side, so this works with no JavaScript at all. The job here has no
    # licence report, so the tab renders its no-data notice — which is still proof that the
    # LICENCES tab, not the Overview, was the one rendered for ?tab=licenses.
    assert "licence report is available" in html
    assert "Total packages" not in html
    assert 'aria-selected="true"' in html


@pytest.mark.django_db
def test_an_unknown_tab_falls_back_to_overview(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}?tab=nonsense").content.decode()

    assert "Total packages" in html


@pytest.mark.django_db
def test_tabs_load_their_content_over_htmx(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}").content.decode()

    assert f"/results/{job.task_id}/tab/vulnerabilities" in html
    # Story 22.21: the whole panel is the target, tab strip included. Targeting the body alone
    # left the strip as first rendered, so the clicked tab's content appeared while "Overview"
    # stayed highlighted.
    assert 'hx-target="#tab-panel"' in html
    assert 'hx-swap="outerHTML"' in html
    # The URL is pushed so a click leaves a shareable address behind.
    assert 'hx-push-url="?tab=vulnerabilities"' in html


@pytest.mark.django_db
@pytest.mark.parametrize("tab", [slug for slug, _label in RESULT_TABS])
def test_each_tab_partial_renders(org_client, tab: str) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    response = client.get(f"/results/{job.task_id}/tab/{tab}")

    assert response.status_code == 200
    assert response.content.strip()


@pytest.mark.django_db
def test_no_tab_is_a_placeholder_any_more(org_client) -> None:  # type: ignore[no-untyped-def]
    """Stories 21.13-21.16 filled in all four detail tabs.

    This replaces the placeholder check rather than deleting it: the shell must now render
    real content for every tab, and a reintroduced "arrives in Story" stub would mean a tab
    regressed.
    """
    client, org = org_client
    job = _job(org)

    for slug, _label in RESULT_TABS:
        body = client.get(f"/results/{job.task_id}/tab/{slug}").content.decode().lower()
        assert "arrives in story" not in body, f"{slug} is still a placeholder"
        assert body.strip()


@pytest.mark.django_db
def test_an_unrecognised_tab_partial_is_404(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)
    assert client.get(f"/results/{job.task_id}/tab/wat").status_code == 404


# --- AC #2: no existence leak --------------------------------------------------------------


@pytest.mark.django_db
def test_another_orgs_results_render_while_an_unknown_id_404s(org_client) -> None:  # type: ignore[no-untyped-def]
    """Story 22.16 inverted this: the two cases are now meant to differ.

    It used to assert the two responses were byte-identical, so a caller could not learn that
    another org's job existed. With History listing every org that secret no longer exists to
    keep, and the rows have to open. The unknown id is the only refusal left.
    """
    client, _ = org_client
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org)

    cross_org = client.get(f"/results/{theirs.task_id}")
    missing = client.get("/results/00000000-0000-0000-0000-000000000000")

    assert cross_org.status_code == 200
    assert missing.status_code == 404


@pytest.mark.django_db
def test_cross_org_tab_partials_are_also_served(org_client) -> None:  # type: ignore[no-untyped-def]
    client, _ = org_client
    outsider = register_user(email="outsider@example.com", password=PASSWORD)
    other_org = create_org(name="Other", admin_user=outsider)
    theirs = _job(other_org)

    assert client.get(f"/results/{theirs.task_id}/tab/overview").status_code == 200


# --- AC #3: Overview reads only summary_stats ---------------------------------------------


@pytest.mark.django_db
def test_the_overview_cards_render_from_summary_stats(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}").content.decode()

    assert "42" in html  # total packages
    assert "3 vulnerable" in html
    assert "30 permissive" in html
    assert "20 current" in html


@pytest.mark.django_db
def test_the_overview_does_not_read_the_artifact_store(org_client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """NFR-2.2: summary_stats exists so four cards cost zero artifact reads."""
    from django.core.files.storage import default_storage

    client, org = org_client
    job = _job(org)

    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("the Overview must not touch artifact storage")

    monkeypatch.setattr(default_storage, "open", _boom)
    monkeypatch.setattr(default_storage, "url", _boom)

    assert client.get(f"/results/{job.task_id}").status_code == 200


@pytest.mark.django_db
def test_each_metric_deep_links_to_its_tab(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}").content.decode()

    for tab in ("vulnerabilities", "licenses", "versions"):
        assert f'href="?tab={tab}"' in html


@pytest.mark.django_db
def test_the_sbom_download_points_at_the_presigned_endpoint(org_client) -> None:  # type: ignore[no-untyped-def]
    # AD-11: Django 303s to storage and never streams artifact bytes, so the page links at the
    # existing endpoint rather than proxying the download through a new view.
    client, org = org_client
    job = _job(org)

    html = client.get(f"/results/{job.task_id}").content.decode()

    assert f"/api/v1/sbom/result/{job.task_id}/" in html


# --- AC #4: a failed phase is "Unavailable", never 0 ---------------------------------------


def test_a_failed_phase_reads_unavailable_rather_than_zero() -> None:
    stats = {
        "total_packages": 10,
        "reports": {
            "vuln": {"failed": True, "failure_reason": "nvd_unavailable"},
            "license": {"failed": False, "Permissive": 5},
            "version": {"failed": False, "current": 5},
        },
    }

    metrics = {metric.title: metric for metric in build_metrics(stats)}

    assert metrics["Vulnerabilities"].value == UNAVAILABLE
    assert metrics["Vulnerabilities"].unavailable is True
    # ...and the rest of the Overview still renders.
    assert metrics["Licenses"].value.startswith("5 permissive")
    assert metrics["Total packages"].value == "10"


def test_a_missing_report_is_also_unavailable() -> None:
    # Absent is not the same as zero either — the phase may simply not have run.
    metrics = {metric.title: metric for metric in build_metrics({"total_packages": 1})}
    for title in ("Vulnerabilities", "Licenses", "Version currency"):
        assert metrics[title].value == UNAVAILABLE


def test_empty_summary_stats_do_not_raise() -> None:
    metrics = build_metrics({})
    assert metrics[0].value == "0"  # total packages genuinely is zero
    assert all(metric.value == UNAVAILABLE for metric in metrics[1:])


@pytest.mark.django_db
def test_a_failed_phase_renders_unavailable_on_the_page(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    stats = dict(FULL_STATS)
    stats["reports"] = {**FULL_STATS["reports"], "vuln": {"failed": True, "failure_reason": "nvd_unavailable"}}
    job = _job(org, stats=stats)

    html = client.get(f"/results/{job.task_id}").content.decode()

    assert UNAVAILABLE in html
    assert "30 permissive" in html  # the rest of the Overview is unaffected


# --- AC #5: purged artifacts degrade to summary-only ---------------------------------------


@pytest.mark.django_db
def test_a_purged_job_shows_the_warning_and_the_overview(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, purged=True)

    html = client.get(f"/results/{job.task_id}").content.decode()

    assert "Artifacts removed" in html
    assert "42" in html  # the summary is retained permanently (Story 7.3)


@pytest.mark.django_db
def test_a_purged_job_offers_no_download_and_no_detail_tabs(org_client) -> None:  # type: ignore[no-untyped-def]
    client, org = org_client
    job = _job(org, purged=True)

    html = client.get(f"/results/{job.task_id}").content.decode()

    assert f"/api/v1/sbom/result/{job.task_id}/" not in html
    # The detail tabs are disabled rather than linking to something that cannot load.
    assert 'aria-disabled="true"' in html


# --- Access --------------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_running_job_still_shows_the_progress_gate(org_client) -> None:  # type: ignore[no-untyped-def]
    # Story 21.11's gate must survive the shell being added on top of it.
    client, org = org_client
    job = _job(org, status=SBOMJob.Status.PROGRESS)

    html = client.get(f"/results/{job.task_id}").content.decode()

    assert 'hx-trigger="every 5s"' in html
    assert "Total packages" not in html


@pytest.mark.django_db
@pytest.mark.parametrize("tab", [slug for slug, _label in RESULT_TABS])
def test_the_clicked_tab_is_the_one_marked_active(org_client, tab: str) -> None:  # type: ignore[no-untyped-def]
    """Story 22.21: the strip and the body must never disagree about which tab is showing.

    htmx swapped only `#tab-content`, so the `active` class stayed exactly where the server
    first put it — the Version Currency table would render under a highlighted "Overview", with
    the clicked tab showing nothing but a focus outline.

    Asserted on the fragment htmx actually receives, per tab, because the bug was invisible on
    first load and appeared only after a click.
    """
    import re

    client, org = org_client
    job = _job(org)

    fragment = client.get(f"/results/{job.task_id}/tab/{tab}").content.decode()

    active = re.findall(r'<a class="nav-link active"[^>]*hx-push-url="\?tab=([a-z]+)"', fragment)
    assert active == [tab], f"expected only {tab} active, got {active}"


@pytest.mark.django_db
def test_the_tab_fragment_carries_the_whole_strip(org_client) -> None:  # type: ignore[no-untyped-def]
    """The fragment replaces the panel, so it has to bring every tab with it.

    Returning only the body would leave the user with no way back to the other tabs.
    """
    client, org = org_client
    job = _job(org)

    fragment = client.get(f"/results/{job.task_id}/tab/licenses").content.decode()

    assert 'id="tab-panel"' in fragment
    for slug, _label in RESULT_TABS:
        assert f"/tab/{slug}" in fragment, slug
