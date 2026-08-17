"""Story 21.4: server-side access control, tested as the security boundary it is.

The SPA's route guards described themselves as "UX, not the security boundary" — the API
was the boundary behind them. Server-rendered pages have no such second line: these mixins
*are* the boundary. So the matrix below is exhaustive rather than representative, and it
asserts status codes rather than "a redirect happened", because the distinction between
redirect and 403 is the substance of AC #1.

The views under test are defined here, not imported. No business page exists until Story
21.5, and testing the mixins through a real page would conflate the gate with the page.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from django.http import HttpResponse
from django.test import Client
from django.urls import path
from django.views.generic import View

from config.urls import urlpatterns as project_urlpatterns
from inventory.common.access import (
    GlobalAdminRequiredMixin,
    OrgAdminRequiredMixin,
    OrgMemberRequiredMixin,
    get_org_scoped_object_or_404,
)
from inventory.manifests.models import ManifestUpload
from inventory.users.models import Org, OrgMembership
from inventory.users.services import create_org, grant_global_admin, register_user

PASSWORD = "pw12345678"
LOGIN_PREFIX = "/login"


def _manifest(org: Org) -> ManifestUpload:
    """Create a minimal org-owned manifest (every provenance field is required)."""
    return ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/test/requirements.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
        application_id="APP-1",
        component_name="component",
        repository_url="https://example.com/repo",
        source_branch="main",
    )


# --- Views existing only for this test module -------------------------------------------


class _MemberPage(OrgMemberRequiredMixin, View):
    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        # Echoes the resolved org so the tests can prove `self.org` is set and correct.
        return HttpResponse(f"member:{self.org.slug}")


class _AdminPage(OrgAdminRequiredMixin, View):
    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        return HttpResponse(f"admin:{self.org.slug}")


class _GlobalAdminPage(GlobalAdminRequiredMixin, View):
    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        return HttpResponse("global-admin")


class _ScopedDetail(OrgMemberRequiredMixin, View):
    """Stands in for every org-scoped detail page (AC #5)."""

    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        obj = get_org_scoped_object_or_404(ManifestUpload, self.org, pk=kwargs["pk"])
        return HttpResponse(f"manifest:{obj.pk}")


# The project's own patterns are appended, not replaced: `base.html` reverses
# `org-switch`, and the 403 page extends the shell — so a urlconf without the real routes
# would fail to render the very responses these tests assert on.
urlpatterns = [
    path("t/member/", _MemberPage.as_view()),
    path("t/admin/", _AdminPage.as_view()),
    path("t/global/", _GlobalAdminPage.as_view()),
    path("t/manifest/<uuid:pk>/", _ScopedDetail.as_view()),
    *project_urlpatterns,
]

pytestmark = pytest.mark.urls(__name__)


# --- Principals -------------------------------------------------------------------------


def _client_for(email: str, *, org: str | None = None, admin: bool = False, global_admin: bool = False) -> Client:
    user = register_user(email=email, password=PASSWORD)
    if org is not None:
        create_org(name=org, admin_user=user)
        if not admin:
            OrgMembership.objects.filter(user=user).update(role=OrgMembership.Role.MEMBER)
    if global_admin:
        grant_global_admin(user)
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


@pytest.fixture
def anonymous() -> Client:
    return Client()


@pytest.fixture
def member() -> Client:
    return _client_for("member@example.com", org="Acme")


@pytest.fixture
def org_admin() -> Client:
    return _client_for("admin@example.com", org="Acme", admin=True)


@pytest.fixture
def global_admin() -> Client:
    return _client_for("root@example.com", org="Acme", admin=True, global_admin=True)


@pytest.fixture
def zero_org() -> Client:
    return _client_for("nobody@example.com")


# --- AC #1: anonymous redirects, wrong role is 403 ---------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/t/member/", "/t/admin/", "/t/global/"])
def test_anonymous_is_redirected_to_login_preserving_the_destination(anonymous: Client, url: str) -> None:
    response = anonymous.get(url)
    assert response.status_code == 302
    assert response.headers["Location"].startswith(LOGIN_PREFIX)
    # Without `next` the user lands on the login page and then loses their way — the
    # destination has to survive the round trip.
    assert f"next={url}" in response.headers["Location"]


@pytest.mark.django_db
def test_member_reaches_a_member_page(member: Client) -> None:
    response = member.get("/t/member/")
    assert response.status_code == 200
    assert response.content == b"member:acme"


@pytest.mark.django_db
def test_member_is_forbidden_from_an_admin_page_not_redirected(member: Client) -> None:
    # The crux of AC #1: an authenticated user lacking the role gets 403. A redirect here
    # would turn an authorization failure into a navigation event.
    assert member.get("/t/admin/").status_code == 403


@pytest.mark.django_db
def test_member_is_forbidden_from_a_global_admin_page(member: Client) -> None:
    assert member.get("/t/global/").status_code == 403


@pytest.mark.django_db
def test_org_admin_reaches_member_and_admin_pages(org_admin: Client) -> None:
    assert org_admin.get("/t/member/").status_code == 200
    assert org_admin.get("/t/admin/").status_code == 200


@pytest.mark.django_db
def test_org_admin_is_forbidden_from_a_global_admin_page(org_admin: Client) -> None:
    # Org admin is not the platform tier — this is the privilege boundary between them.
    assert org_admin.get("/t/global/").status_code == 403


@pytest.mark.django_db
def test_global_admin_reaches_every_page(global_admin: Client) -> None:
    assert global_admin.get("/t/member/").status_code == 200
    assert global_admin.get("/t/admin/").status_code == 200
    assert global_admin.get("/t/global/").status_code == 200


# --- AC #4: zero-org users -------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/t/member/", "/t/admin/"])
def test_zero_org_user_gets_the_no_org_state_on_org_scoped_pages(zero_org: Client, url: str) -> None:
    response = zero_org.get(url)
    assert response.status_code == 200
    body = response.content.decode()
    # The page's own content must NOT be served...
    assert "member:" not in body
    assert "admin:" not in body
    # ...and the shared empty state must be, identically on every org-scoped page.
    assert "No organization yet" in body


@pytest.mark.django_db
def test_zero_org_global_admin_still_reaches_platform_pages() -> None:
    """A global admin with no working org must not be locked out of the platform tier.

    Story 2.18 makes the ADMIN org never resolve as a working org, so this user has **no**
    active org at all. If GlobalAdminRequiredMixin required one, the global-admin page
    would be unreachable by exactly the people it is for.
    """
    user = register_user(email="platform@example.com", password=PASSWORD)
    grant_global_admin(user)
    client = Client()
    assert client.login(email="platform@example.com", password=PASSWORD)

    assert client.get("/t/global/").status_code == 200
    # ...while org-scoped pages correctly show the no-org state.
    assert "No organization yet" in client.get("/t/member/").content.decode()


@pytest.mark.django_db
def test_no_org_state_offers_create_only_to_global_admins(zero_org: Client) -> None:
    # Only global admins may create orgs (Story 2.12); offering a button that would 403 is
    # worse than offering none.
    assert "Create organization" not in zero_org.get("/t/member/").content.decode()


# --- AC #5: cross-org requests must not leak existence ---------------------------------


@pytest.mark.django_db
def test_cross_org_and_missing_objects_are_indistinguishable() -> None:
    """The heart of AD-2: a 404-vs-403 difference would confirm the object exists."""
    owner = register_user(email="owner@example.com", password=PASSWORD)
    org_a = create_org(name="Org A", admin_user=owner)
    theirs = _manifest(org_a)

    outsider = _client_for("outsider@example.com", org="Org B")

    cross_org = outsider.get(f"/t/manifest/{theirs.pk}/")
    missing = outsider.get(f"/t/manifest/{uuid4()}/")

    assert cross_org.status_code == missing.status_code == 404
    # Not just the same status — the same response, so nothing distinguishes them.
    assert cross_org.content == missing.content


@pytest.mark.django_db
def test_owner_can_read_their_own_org_scoped_object() -> None:
    # Guards against the previous test passing because the view is simply broken.
    owner = register_user(email="owner2@example.com", password=PASSWORD)
    org = create_org(name="Org C", admin_user=owner)
    mine = _manifest(org)
    client = Client()
    assert client.login(email="owner2@example.com", password=PASSWORD)

    response = client.get(f"/t/manifest/{mine.pk}/")
    assert response.status_code == 200
    assert response.content == f"manifest:{mine.pk}".encode()


# --- Admin-ness is per active org ------------------------------------------------------


@pytest.mark.django_db
def test_admin_of_one_org_is_not_admin_after_switching_to_another() -> None:
    """`is_admin` is per-active-org, and the Dev Notes ask for this transition explicitly.

    A user who administers org A and merely belongs to org B must lose admin access the
    moment B becomes active — otherwise the gate is checking the user, not the org.
    """
    user = register_user(email="dual@example.com", password=PASSWORD)
    org_a = create_org(name="Alpha", admin_user=user)
    org_b = Org.objects.create(name="Beta", slug="beta")
    OrgMembership.objects.create(org=org_b, user=user, role=OrgMembership.Role.MEMBER)

    client = Client()
    assert client.login(email="dual@example.com", password=PASSWORD)

    # Active org resolves to Alpha (admin there) → admin page allowed.
    session = client.session
    session["active_org_id"] = org_a.pk
    session.save()
    assert client.get("/t/admin/").status_code == 200

    # Switch to Beta, where the same user is only a member → 403.
    session = client.session
    session["active_org_id"] = org_b.pk
    session.save()
    assert client.get("/t/admin/").status_code == 403
    # ...but member pages still work, against the newly active org.
    assert client.get("/t/member/").content == b"member:beta"
