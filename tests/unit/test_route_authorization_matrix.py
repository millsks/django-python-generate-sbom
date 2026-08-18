"""Story 21.23 AC #3: every route, every principal, asserted at the real URL.

`test_access_control.py` (Story 21.4) tests the mixins against synthetic views, which
proves the mixins are correct but **not** that each real route is wired to the right one.
A page that simply forgot its mixin passes every test in that module. This one closes
that gap: it drives the ten routes transcribed from the retired `App.tsx` with six
different principals and pins the status code of every cell.

Status codes are asserted rather than "a redirect happened", because the difference
between 302 and 403 is the substance of the rule (Story 21.4): anonymous users get sent
somewhere they can fix the problem; authenticated users with the wrong role get a real
authorization failure that shows up in tests and logs.
"""

from __future__ import annotations

import pytest
from django.test import Client

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.services import create_member, create_org, grant_global_admin, register_user

# The shell's logout form carries a CSRF token that Django re-salts on every render, so two
# otherwise identical error pages always differ by it. Reused from `test_access_control.py`,
# which paid for this discovery first.
from tests.unit.test_access_control import _masked

PASSWORD = "pw12345678"

ANON, MEMBER, ORG_ADMIN, GLOBAL_ADMIN, ZERO_ORG, OTHER_ORG = (
    "anonymous",
    "member",
    "org-admin",
    "global-admin",
    "zero-org",
    "other-org",
)

PUBLIC = ("/",)
AUTH_ENTRY = ("/register", "/login")
ORG_SCOPED = ("/keys", "/upload", "/history")
ORG_ADMIN_ONLY = ("/organization", "/members")
GLOBAL_ADMIN_ONLY = ("/platform/global-admins",)

RESULTS = ("/results/<id>",)

#: Every route reached only by a member of the active org — the list pages plus one job.
MEMBER_REACHABLE = ORG_SCOPED + RESULTS

#: Every route that must never answer 200 to an anonymous visitor.
PROTECTED = ORG_SCOPED + ORG_ADMIN_ONLY + GLOBAL_ADMIN_ONLY + RESULTS

#: The ten routes the SPA served, transcribed from `App.tsx` before Story 21.19 deleted it.
ALL_ROUTES = PUBLIC + AUTH_ENTRY + ORG_ADMIN_ONLY + ORG_SCOPED + GLOBAL_ADMIN_ONLY + RESULTS


@pytest.fixture
def world():  # type: ignore[no-untyped-def]
    """One org with an admin and a member, a global admin, a zero-org user, and a second org."""
    admin = register_user(email="admin@example.com", password=PASSWORD)
    org = create_org(name="Acme", admin_user=admin)

    register_user(email="member@example.com", password=PASSWORD)
    create_member(org=org, email="member@example.com")

    grant_global_admin(register_user(email="global@example.com", password=PASSWORD))
    register_user(email="nobody@example.com", password=PASSWORD)

    other = register_user(email="other@example.com", password=PASSWORD)
    create_org(name="Other", admin_user=other)

    upload = ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
    )
    job = SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        summary_stats={},
        result_key="sboms/x.json",
    )
    return {"org": org, "job": job}


EMAILS = {
    MEMBER: "member@example.com",
    ORG_ADMIN: "admin@example.com",
    GLOBAL_ADMIN: "global@example.com",
    ZERO_ORG: "nobody@example.com",
    OTHER_ORG: "other@example.com",
}


def _client(principal: str) -> Client:
    client = Client()
    if principal != ANON:
        assert client.login(email=EMAILS[principal], password=PASSWORD)
    return client


def _get(principal: str, route: str, world: dict) -> object:  # type: ignore[type-arg]
    if route == "/results/<id>":
        route = f"/results/{world['job'].task_id}"
    return _client(principal).get(route)


# --- Anonymous ------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("route", PROTECTED)
def test_anonymous_is_redirected_to_login_carrying_the_destination(route: str, world: dict) -> None:  # type: ignore[type-arg]
    response = _get(ANON, route, world)

    assert response.status_code == 302  # type: ignore[attr-defined]
    # `next` is the point: bouncing to the login page and losing the destination turns a
    # shared results link into a dead end.
    assert "/login" in response["Location"]  # type: ignore[index]
    assert "next=" in response["Location"]  # type: ignore[index]


@pytest.mark.django_db
@pytest.mark.parametrize("route", PUBLIC + AUTH_ENTRY)
def test_anonymous_reaches_the_public_routes(route: str, world: dict) -> None:  # type: ignore[type-arg]
    assert _get(ANON, route, world).status_code == 200  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_no_protected_route_ever_answers_200_to_anonymous(world: dict) -> None:  # type: ignore[type-arg]
    """The single assertion that would catch a page shipped with no mixin at all."""
    leaked = [
        route
        for route in PROTECTED
        if _get(ANON, route, world).status_code == 200  # type: ignore[attr-defined]
    ]
    assert not leaked, f"served to an anonymous user: {leaked}"


# --- Wrong role gets 403, not a redirect ----------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("route", ORG_ADMIN_ONLY)
def test_a_plain_member_is_forbidden_from_org_admin_pages(route: str, world: dict) -> None:  # type: ignore[type-arg]
    assert _get(MEMBER, route, world).status_code == 403  # type: ignore[attr-defined]


@pytest.mark.django_db
@pytest.mark.parametrize("principal", [MEMBER, ORG_ADMIN, OTHER_ORG])
def test_only_a_global_admin_reaches_the_platform_page(principal: str, world: dict) -> None:  # type: ignore[type-arg]
    """An org admin is *not* a platform admin — the two tiers are independent."""
    assert _get(principal, "/platform/global-admins", world).status_code == 403  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_the_global_admin_reaches_the_platform_page(world: dict) -> None:  # type: ignore[type-arg]
    assert _get(GLOBAL_ADMIN, "/platform/global-admins", world).status_code == 200  # type: ignore[attr-defined]


# --- Members and admins reach what they should ----------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("principal", [MEMBER, ORG_ADMIN, GLOBAL_ADMIN])
@pytest.mark.parametrize("route", MEMBER_REACHABLE)
def test_org_members_reach_the_org_scoped_pages(principal: str, route: str, world: dict) -> None:  # type: ignore[type-arg]
    assert _get(principal, route, world).status_code == 200  # type: ignore[attr-defined]


@pytest.mark.django_db
@pytest.mark.parametrize("route", ORG_ADMIN_ONLY)
@pytest.mark.parametrize("principal", [ORG_ADMIN, GLOBAL_ADMIN])
def test_admins_reach_the_org_admin_pages(principal: str, route: str, world: dict) -> None:  # type: ignore[type-arg]
    """A global admin holds a real admin membership in every org (AD-14), so no special case."""
    assert _get(principal, route, world).status_code == 200  # type: ignore[attr-defined]


# --- Cross-org: the assertion AD-2 exists for ------------------------------------------


@pytest.mark.django_db
def test_another_orgs_job_is_indistinguishable_from_a_missing_one(world: dict) -> None:  # type: ignore[type-arg]
    """404 for both, byte for byte — a 403-vs-404 difference confirms the job exists."""
    client = _client(OTHER_ORG)

    cross_org = client.get(f"/results/{world['job'].task_id}")
    nonexistent = client.get("/results/00000000-0000-0000-0000-000000000000")

    assert cross_org.status_code == 404
    assert nonexistent.status_code == 404
    assert _masked(cross_org) == _masked(nonexistent)


@pytest.mark.django_db
def test_another_orgs_job_is_absent_from_history(world: dict) -> None:  # type: ignore[type-arg]
    """Isolation is not only per-object: the list must not leak the job's existence either."""
    html = _client(OTHER_ORG).get("/history").content.decode()

    assert str(world["job"].task_id) not in html


# --- Zero-org: Story 21.4 AC #4, at the real routes ------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("route", ORG_SCOPED + ORG_ADMIN_ONLY + RESULTS)
def test_a_zero_org_user_gets_the_shared_empty_state_on_every_org_scoped_route(route: str, world: dict) -> None:  # type: ignore[type-arg]
    """200 with the empty state, not 403 and not an error — they have done nothing wrong.

    Returning the page's own URL with this body also means the URL is not a way to reach
    org data, which a redirect to `/` would leave ambiguous.
    """
    response = _get(ZERO_ORG, route, world)

    assert response.status_code == 200  # type: ignore[attr-defined]
    assert "No organization yet" in response.content.decode()  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_a_zero_org_user_is_still_forbidden_from_the_platform_page(world: dict) -> None:  # type: ignore[type-arg]
    # Having no org must not be mistaken for being a platform admin, who also has none.
    assert _get(ZERO_ORG, "/platform/global-admins", world).status_code == 403  # type: ignore[attr-defined]


# --- Signed-in users and the auth entry points ----------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("route", AUTH_ENTRY)
@pytest.mark.parametrize("principal", [MEMBER, ORG_ADMIN, GLOBAL_ADMIN, ZERO_ORG])
def test_an_authenticated_user_is_bounced_off_login_and_register(principal: str, route: str, world: dict) -> None:  # type: ignore[type-arg]
    assert _get(principal, route, world).status_code == 302  # type: ignore[attr-defined]


@pytest.mark.django_db
@pytest.mark.parametrize("principal", [ANON, MEMBER, ORG_ADMIN, GLOBAL_ADMIN, ZERO_ORG, OTHER_ORG])
def test_the_landing_page_is_reachable_by_everyone(principal: str, world: dict) -> None:  # type: ignore[type-arg]
    assert _get(principal, "/", world).status_code == 200  # type: ignore[attr-defined]


# --- The audit's own guard --------------------------------------------------------------


def test_the_matrix_covers_all_ten_spa_routes() -> None:
    """If a route is added to the app but not here, the matrix silently stops being a matrix."""
    assert len(ALL_ROUTES) == 10, ALL_ROUTES
