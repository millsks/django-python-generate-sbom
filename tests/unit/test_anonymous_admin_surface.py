"""Story 22.8: the admin surfaces must work for an anonymous caller, on both paths.

Story 21.24 removed the app's authentication and stated (AC #5) that member management, **org
creation**, API-key create/revoke, bulk artifact deletion, and the platform global-admins page
are all reachable and all succeed. Two things slipped through, and the existing suite could not
see either — because **every** page and API test logs in first, so nothing exercised the path
that is now the ordinary one.

1. **Org creation returned 500 for an anonymous caller**, on the API *and* the page.
   `create_org` assigned `admin_user` to `OrgMembership.user`, and an `AnonymousUser` raises
   `ValueError: Cannot assign ... must be a "User" instance`.

2. **A logged-in ordinary user was MORE restricted than an anonymous one.** Four DRF views kept
   an in-body `is_global_admin(...)` check. `is_global_admin` returns `True` for anonymous
   (Story 21.24) but does the real membership query for a real user — so signing in *lost* you
   access. Story 21.24 removed the permission class and the page mixins but missed these copies
   inside view bodies.

The parity tests below are the guard: whatever an anonymous caller can do, a signed-in ordinary
user must be able to do too. That relationship is what inverted, and asserting each side
separately would not have caught it.
"""

from __future__ import annotations

import pytest
from django.test import Client

from inventory.users.models import Org, OrgMembership
from inventory.users.services import create_org, register_user

PASSWORD = "pw12345678"


@pytest.fixture
def ordinary_user_client(db: None) -> Client:
    """A signed-in user who is NOT a global admin and belongs to no org."""
    register_user(email="ordinary@example.com", password=PASSWORD)
    client = Client()
    assert client.login(email="ordinary@example.com", password=PASSWORD)
    return client


# --- Org creation works without a user at all ---------------------------------------------


@pytest.mark.django_db
def test_an_anonymous_caller_can_create_an_org_through_the_api() -> None:
    before = Org.objects.count()

    response = Client().post("/api/v1/orgs/create/", {"name": "Anon API"}, content_type="application/json")

    assert response.status_code == 201, response.content
    assert Org.objects.count() == before + 1


@pytest.mark.django_db
def test_an_anonymous_caller_can_create_an_org_through_the_page() -> None:
    before = Org.objects.count()

    response = Client().post("/organization/create", {"name": "Anon Page"})

    assert response.status_code == 302, response.content
    assert Org.objects.filter(name="Anon Page").exists()
    assert Org.objects.count() == before + 1


@pytest.mark.django_db
def test_an_org_created_anonymously_simply_has_no_admin_membership() -> None:
    """No synthetic user is invented — the same shape as a userless API-key upload.

    Story 21.24's notes rule out inventing a user explicitly: `ManifestUpload.user` and
    `SBOMJob.user` are nullable so userless work can be recorded, and an org with no
    memberships is the equivalent coherent state.
    """
    Client().post("/api/v1/orgs/create/", {"name": "Ownerless"}, content_type="application/json")

    org = Org.objects.get(name="Ownerless")
    assert not OrgMembership.objects.filter(org=org).exists()


@pytest.mark.django_db
def test_a_signed_in_creator_still_becomes_the_admin(ordinary_user_client: Client) -> None:
    """The userless path must not cost the normal one its behaviour."""
    ordinary_user_client.post("/api/v1/orgs/create/", {"name": "Mine"}, content_type="application/json")

    org = Org.objects.get(name="Mine")
    assert OrgMembership.objects.filter(
        org=org, user__email="ordinary@example.com", role=OrgMembership.Role.ADMIN
    ).exists()


# --- Parity: signing in must never take capability away ------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/api/v1/orgs/create/", {"name": "Parity Org"}),
        ("get", "/api/v1/admin/global-admins/", None),
        ("get", "/api/v1/orgs/", None),
        ("get", "/api/v1/keys/", None),
    ],
)
def test_a_signed_in_user_is_never_more_restricted_than_an_anonymous_one(
    method: str, path: str, payload: dict | None, ordinary_user_client: Client
) -> None:
    """The inversion this story fixed, asserted as a relationship rather than two absolutes.

    Both callers may legitimately be refused, or both allowed — what must never happen is the
    anonymous one succeeding where the signed-in one is forbidden.
    """
    create_org(name="Existing", admin_user=None)

    def call(client: Client) -> int:
        if method == "post":
            return client.post(path, payload, content_type="application/json").status_code
        return client.get(path).status_code

    anonymous_status = call(Client())
    signed_in_status = call(ordinary_user_client)

    assert not (anonymous_status < 400 <= signed_in_status), (
        f"{path}: anonymous got {anonymous_status} but a signed-in user got {signed_in_status} — "
        "signing in must not remove capability"
    )


@pytest.mark.django_db
def test_the_global_admin_endpoints_no_longer_gate_on_the_tier(ordinary_user_client: Client) -> None:
    """`is_global_admin` still *reports* truthfully; it no longer *gates* (Story 21.24)."""
    assert ordinary_user_client.get("/api/v1/admin/global-admins/").status_code == 200
    assert Client().get("/api/v1/admin/global-admins/").status_code == 200
