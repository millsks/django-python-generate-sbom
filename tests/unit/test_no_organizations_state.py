"""What the app does when the database contains no organization at all (Story 22.12).

This state is reachable and was almost entirely untested. It is not the old "zero-org user"
(Story 21.24 deleted that concept along with authentication) — it means the deployment has no
workspace: someone deleted every org, or `seed_orgs` was never run against a fresh database.

It matters because **every org-scoped surface depends on `get_request_org` returning
something**, and it returns `None` here. The audit found `common/access.py`'s no-orgs branch
uncovered, and most of `users/views.py`'s uncovered lines turned out to be the same condition
reached through the API — so one scenario closes both.

The rule being pinned: this is a **recoverable data state, not a crash**. Pages explain it,
the API answers with its documented error envelope, and nothing 500s.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import Client

from inventory.users.models import Org

pytestmark = pytest.mark.django_db


# --- The pages explain it rather than erroring ---------------------------------------------


@pytest.mark.parametrize("path", ["/upload", "/job-status", "/keys"])
def test_org_scoped_pages_render_the_no_organizations_state(path: str, no_organizations: None) -> None:
    """200 with an explanation, not a 500 and not a redirect.

    Returning the page's own URL with this body also means the URL is not a way to reach org
    data, which a redirect elsewhere would leave ambiguous.
    """
    response = Client().get(path)

    assert response.status_code == 200
    body = response.content.decode()
    assert "No organizations exist" in body
    assert "seed-orgs" in body, "the page should name the remedy, not just the problem"


def test_the_landing_page_still_works_without_any_organization(no_organizations: None) -> None:
    """The landing page is not org-scoped, so it must be unaffected."""
    assert Client().get("/").status_code == 200


# --- The API answers with its documented shape --------------------------------------------


def test_the_active_org_endpoint_reports_that_there_is_none(no_organizations: None) -> None:
    response = Client().get("/api/v1/orgs/me/")

    assert response.status_code == 404
    assert response.json()["code"], "the error envelope should carry a code"


def test_listing_organizations_returns_an_empty_list(no_organizations: None) -> None:
    """Empty is the truthful answer here — an error would overstate the problem."""
    response = Client().get("/api/v1/orgs/")

    assert response.status_code == 200
    assert response.json() == []


def test_no_api_endpoint_returns_a_server_error(no_organizations: None) -> None:
    """The blanket check: a missing workspace must never be a 500 anywhere.

    Asserted across the surface rather than per endpoint, because the failure mode is a
    forgotten `None` check in whichever view nobody thought about.
    """
    client = Client()
    paths = [
        "/api/v1/orgs/",
        "/api/v1/orgs/me/",
        "/api/v1/keys/",
        "/api/v1/sbom/jobs/",
        "/api/v1/auth/me/",
        "/api/v1/admin/global-admins/",
    ]

    server_errors = [path for path in paths if client.get(path).status_code >= 500]

    assert not server_errors, f"these 500 when no organization exists: {server_errors}"


def test_no_page_returns_a_server_error(no_organizations: None) -> None:
    client = Client()
    paths = ["/", "/upload", "/job-status", "/keys"]

    server_errors = [path for path in paths if client.get(path).status_code >= 500]

    assert not server_errors, f"these 500 when no organization exists: {server_errors}"


# --- Recovery -------------------------------------------------------------------------------


def test_seeding_restores_the_app(no_organizations: None, settings: pytest.FixtureRequest, tmp_path: Path) -> None:
    """The remedy the page names must actually work from this state."""
    listing = tmp_path / "orgs.yml"
    listing.write_text("organizations:\n  - name: Recovered\n    slug: recovered\n", encoding="utf-8")
    settings.INVENTORY_ORGS_FILE = str(listing)  # type: ignore[attr-defined]

    call_command("seed_orgs", stdout=StringIO())

    assert Org.objects.filter(slug="recovered").exists()
    body = Client().get("/upload").content.decode()
    assert "No organizations exist" not in body
    assert "Recovered" in body


# --- Validation errors keep their envelope ---------------------------------------------------


def test_an_invalid_payload_returns_the_error_envelope_not_a_crash() -> None:
    """The `_validation_error` path, which the audit found uncovered."""
    response = Client().post("/api/v1/orgs/create/", {"name": ""}, content_type="application/json")

    assert response.status_code == 400
    body = response.json()
    assert "error" in body and "code" in body, body
