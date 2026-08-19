"""Story 22.16: the header org switcher is gone, and the organization is per-job instead.

The switcher put the whole UI into a mode. Since Story 21.24 removed authentication it also
accepted **any** non-ADMIN org from **anyone**, so the mode it selected was not a permission —
it was a filter with a misleading shape, two clicks from the page you were reading.

The organization is now what it always meant: provenance on a job. It is chosen on the upload
form (Story 21.9), shown as a column on History, and written into the generated SBOM as its
supplier (Story 22.14). This module is what stops the switcher coming back, and pins the three
surfaces that replaced it.

`tests/unit/test_org_switcher.py` — 14 tests covering the control's CSRF, its `next` handling,
and its refusal of the ADMIN org — was deleted with it. That behaviour has no subject any more;
keeping the tests would have meant keeping the view.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.test import Client
from django.urls import NoReverseMatch, reverse

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org

SRC = Path(__file__).resolve().parents[2] / "src"

pytestmark = pytest.mark.django_db


def _job(org: Org, component: str = "svc") -> SBOMJob:
    upload = ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
        component_name=component,
    )
    return SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        summary_stats={},
    )


# --- The control is gone ---------------------------------------------------------------------


def test_the_switcher_route_no_longer_resolves() -> None:
    with pytest.raises(NoReverseMatch):
        reverse("ui-org-switch")


def test_the_switcher_view_is_deleted() -> None:
    """A deletion story needs a test that fails if the code comes back."""
    from django_service import views

    assert not hasattr(views, "OrgSwitchView")


def test_the_switcher_template_is_deleted() -> None:
    assert not (SRC / "django_service" / "templates" / "_org_switcher.html").exists()


def test_no_template_still_includes_the_switcher() -> None:
    """Deleting the partial without removing its `{% include %}` would 500 every page."""
    offenders = [
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.html")
        if "_org_switcher" in path.read_text(encoding="utf-8")
    ]

    assert not offenders, f"still including the deleted switcher: {offenders}"


def test_the_shell_renders_without_it(default_org: Org) -> None:
    """The assertion above only proves the include is gone; this proves the page still works."""
    for path in ("/", "/upload", "/history", "/keys"):
        assert Client().get(path).status_code == 200, path


def test_no_page_offers_a_way_to_switch_the_active_org(default_org: Org) -> None:
    Org.objects.create(name="Second", slug="second")

    body = Client().get("/history").content.decode()

    assert "org-switcher" not in body
    assert "Active organization" not in body


# --- What replaced it -------------------------------------------------------------------------


def test_the_upload_form_is_where_the_organization_is_chosen(default_org: Org) -> None:
    Org.objects.create(name="Capital Markets", slug="capital-markets")

    body = Client().get("/upload").content.decode()

    assert 'name="org"' in body
    assert "Capital Markets" in body


def test_history_lists_every_organization(default_org: Org) -> None:
    """The switcher's real job — telling you which tenant you were looking at — moved here."""
    other = Org.objects.create(name="Capital Markets", slug="capital-markets")
    mine = _job(default_org, component="mine")
    theirs = _job(other, component="theirs")

    body = Client().get("/history").content.decode()

    assert str(mine.task_id) in body
    assert str(theirs.task_id) in body
    assert "Organization" in body, "the column header"
    assert "Capital Markets" in body


def test_history_can_be_filtered_to_one_organization(default_org: Org) -> None:
    """Filtering replaces switching: the same narrowing, without a mode to forget you are in."""
    other = Org.objects.create(name="Capital Markets", slug="capital-markets")
    mine = _job(default_org, component="mine")
    theirs = _job(other, component="theirs")

    body = Client().get(f"/history?org={other.pk}").content.decode()

    assert str(theirs.task_id) in body
    assert str(mine.task_id) not in body


def test_an_unknown_org_filter_does_not_error(default_org: Org) -> None:
    """Story 6.4's rule: a filter value the backend cannot honour yields a page, not a 500."""
    response = Client().get("/history?org=999999")

    assert response.status_code == 200


# --- The API keeps its scoping ------------------------------------------------------------------


def test_the_api_still_scopes_jobs_to_the_callers_org(default_org: Org) -> None:
    """AD-2 was narrowed to the API, not abandoned.

    An API key pins one tenant (AD-8), and a programmatic caller must still never see another
    org's jobs — which is why `get_jobs` stayed org-scoped while the pages moved to
    `get_all_jobs`.
    """
    from inventory.sbom.selectors import get_all_jobs, get_jobs

    other = Org.objects.create(name="Capital Markets", slug="capital-markets")
    _job(default_org, component="mine")
    theirs = _job(other, component="theirs")

    assert theirs not in get_jobs(default_org)
    assert theirs in get_all_jobs()
