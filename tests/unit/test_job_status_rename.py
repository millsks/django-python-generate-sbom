"""Story 22.17: the History page is called Job Status, on both surfaces.

"History" described half of what the page does. It has shown *running* jobs since Story 21.11
added live progress polling, so someone watching a job they just submitted was looking at a
page named for the past.

The two surfaces moved by different amounts, deliberately:

- **The UI renamed its paths.** `/history` → `/job-status`, the child routes with it, and the
  `ui-history` route name. A rename that leaves the address bar saying "history" is half-done,
  and there are no external bookmarks to protect.
- **The API kept its paths.** `/api/v1/sbom/jobs/` stays, because Story 21.24 AC #9 froze the
  `/api/v1/` contract and `/sbom/status/{task_id}/` already owns "status" for a single job — a
  `/sbom/job-status/` list beside it would be worse than the inconsistency it fixed. Only the
  documented name moved, so the reference and the UI agree on what to call this.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.test import Client
from django.urls import NoReverseMatch, reverse

from inventory.users.models import Org

SRC = Path(__file__).resolve().parents[2] / "src"

pytestmark = pytest.mark.django_db


# --- The UI moved ------------------------------------------------------------------------------


def test_the_page_is_served_at_its_new_path(default_org: Org) -> None:
    assert Client().get("/job-status").status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/history", "/history/artifacts/delete", "/history/artifacts/delete-all"],
)
def test_the_old_paths_are_gone(path: str, default_org: Org) -> None:
    """No redirect, no alias. A rename that leaves the old URL working is two names, not one."""
    assert Client().get(path).status_code == 404


def test_the_old_route_name_no_longer_resolves() -> None:
    with pytest.raises(NoReverseMatch):
        reverse("ui-history")


def test_the_new_route_name_resolves_to_the_new_path() -> None:
    assert reverse("ui-job-status") == "/job-status"


def test_the_child_routes_moved_with_it() -> None:
    """The delete and polling endpoints sat under `/history/`; a half-move would strand them."""
    for name in ("ui-jobs-delete-artifacts", "ui-jobs-delete-all-artifacts"):
        assert reverse(name).startswith("/job-status/"), name
    assert reverse("ui-job-row", args=["00000000-0000-0000-0000-000000000000"]).startswith("/job-status/")


def test_the_browser_tab_says_job_status(default_org: Org) -> None:
    """The `{% block title %}` was missed by the original rename and shipped saying "History".

    Nothing caught it because the other guards check `reverse()` names, nav labels and template
    `{% url %}` calls — none of which the title block touches. The tab is the one piece of a
    page a user reads without scrolling, so it gets its own assertion.
    """
    import re

    body = Client().get("/job-status").content.decode()
    title = re.search(r"<title>(.*?)</title>", body, re.DOTALL)

    assert title is not None
    assert "History" not in title.group(1)
    assert "Job status" in title.group(1)


def test_no_template_still_renders_history_as_a_page_title() -> None:
    """Asserted across every template, since only one page's title was wrong and by inspection."""
    offenders = [
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.html")
        if "block title" in path.read_text(encoding="utf-8")
        and "History" in path.read_text(encoding="utf-8").split("block title")[1].split("endblock")[0]
    ]

    assert not offenders, f"these still title themselves History: {offenders}"


def test_the_page_and_the_nav_both_say_job_status(default_org: Org) -> None:
    body = Client().get("/job-status").content.decode()

    assert "Job status" in body, "the page heading"
    assert "Job Status" in body, "the nav entry"


def test_nothing_still_says_history_in_the_navigation(default_org: Org) -> None:
    """Both names in the nav would be the same drift, pointing the other way."""
    body = Client().get("/job-status").content.decode()

    assert ">History</span>" not in body


def test_no_template_still_reverses_the_old_route_name() -> None:
    """A missed `{% url 'ui-history' %}` raises at render time, not at import.

    Only the page that contains it would fail, which is exactly the kind of miss that reaches a
    branch — so it is asserted across every template rather than by visiting each page.
    """
    offenders = [
        str(path.relative_to(SRC)) for path in SRC.rglob("*.html") if "ui-history" in path.read_text(encoding="utf-8")
    ]

    assert not offenders, f"still reversing the removed route name: {offenders}"


def test_the_results_page_links_back_by_the_new_name(default_org: Org) -> None:
    """The back-link said "Back to history"; leaving it would name a page that no longer exists."""
    source = (SRC / "django_apps/inventory/templates/inventory/sbom/results.html").read_text(encoding="utf-8")

    assert "Back to job status" in source
    assert "Back to history" not in source


# --- The API did not move ------------------------------------------------------------------------


def test_the_api_path_is_unchanged(default_org: Org) -> None:
    """Story 21.24 AC #9 froze this contract; the rename must not break a client."""
    assert Client().get("/api/v1/sbom/jobs/").status_code == 200
    assert reverse("sbom-jobs") == "/api/v1/sbom/jobs/"


def test_no_job_status_path_was_added_to_the_api() -> None:
    """The tempting rename would collide with the single-job status endpoint."""
    assert Client().get("/api/v1/sbom/job-status/").status_code == 404
    assert reverse("sbom-status", args=["00000000-0000-0000-0000-000000000000"]).startswith("/api/v1/sbom/status/")


def test_the_schema_calls_it_job_status() -> None:
    """What did move: the documented name, so the reference and the UI agree."""
    response = Client().get("/api/schema/?format=json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/v1/sbom/jobs/"]["get"]

    assert operation["summary"] == "List job status"
    assert "Job Status" in operation["tags"]
