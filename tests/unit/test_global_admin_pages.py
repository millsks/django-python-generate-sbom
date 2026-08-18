"""Story 21.8: the platform-administration page.

This page grants the highest privilege in the system, so the denial tests are the point of
the module. They assert the status code **and** that no administrator's email appears in the
response body — a 403 that still rendered the roster would leak the platform-admin list to
anyone who typed the URL.

Story 2.17 exists because admin-only pages were once enforced in the navigation alone. These
tests exist so that is not repeated at the global tier.
"""

from __future__ import annotations

import pytest
from django.test import Client

from inventory.users.auth import get_request_org
from inventory.users.models import Org, OrgMembership
from inventory.users.services import (
    create_member,
    create_org,
    grant_global_admin,
    is_global_admin,
    register_user,
)


def _resolved_org(client: Client) -> Org | None:
    """Return the org a request from this client would act as.

    Built through the real request cycle rather than by calling the selector directly, so
    the session state the test just set is actually exercised.
    """
    from django.test import RequestFactory

    request = RequestFactory().get("/")
    request.session = client.session  # type: ignore[attr-defined]
    request.user = client.session and _user_for(client)  # type: ignore[attr-defined]
    return get_request_org(request)


def _user_for(client: Client):  # type: ignore[no-untyped-def]
    """Resolve the logged-in user behind a test client, or AnonymousUser."""
    from django.contrib.auth import get_user
    from django.contrib.auth.models import AnonymousUser

    request = type("R", (), {"session": client.session})()
    try:
        return get_user(request)  # type: ignore[arg-type]
    except Exception:  # pragma: no cover - defensive; anonymous is the fallback
        return AnonymousUser()


PASSWORD = "pw12345678"

PAGE = "/platform/global-admins"
GRANT = "/platform/global-admins/grant"
REVOKE = "/platform/global-admins/revoke"

ALL_URLS = [PAGE, GRANT, REVOKE]

# Every global admin in these tests carries this in their address, so a denial test can assert
# no tier member's identity leaked regardless of which fixture created them.
ADMIN_MARKER = "platform-admin"


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


def _global_admin(email: str):  # type: ignore[no-untyped-def]
    user = register_user(email=email, password=PASSWORD)
    grant_global_admin(user)
    return user


@pytest.fixture
def platform_admin():  # type: ignore[no-untyped-def]
    """A global admin, plus the org they administer."""
    user = register_user(email=f"{ADMIN_MARKER}-1@example.com", password=PASSWORD)
    create_org(name="Acme", admin_user=user)
    grant_global_admin(user)
    return _client(f"{ADMIN_MARKER}-1@example.com"), user


@pytest.fixture
def org_admin_client(platform_admin) -> Client:  # type: ignore[no-untyped-def]
    """An admin of a normal org — privileged, but not on the platform tier."""
    admin = register_user(email="org-admin@example.com", password=PASSWORD)
    create_org(name="Beta", admin_user=admin)
    return _client("org-admin@example.com")


@pytest.fixture
def member_client(platform_admin) -> Client:  # type: ignore[no-untyped-def]
    """A plain member of the platform admin's org."""
    _, _ = platform_admin
    register_user(email="member@example.com", password=PASSWORD)
    org = OrgMembership.objects.filter(org__name="Acme").first().org
    create_member(org, email="member@example.com")
    OrgMembership.objects.filter(user__email="member@example.com").update(role=OrgMembership.Role.MEMBER)
    return _client("member@example.com")


# --- AC #1: the page works for the tier ---------------------------------------------------


@pytest.mark.django_db
def test_a_global_admin_sees_the_tier(platform_admin) -> None:  # type: ignore[no-untyped-def]
    client, user = platform_admin
    html = client.get(PAGE).content.decode()

    assert user.email in html
    assert "Grant global admin" in html


@pytest.mark.django_db
def test_granting_by_email_adds_someone_to_the_tier(platform_admin) -> None:  # type: ignore[no-untyped-def]
    client, _ = platform_admin
    register_user(email="newcomer@example.com", password=PASSWORD)

    client.post(GRANT, {"email": "newcomer@example.com"}, follow=True)

    assert "newcomer@example.com" in client.get(PAGE).content.decode()


@pytest.mark.django_db
def test_granting_to_an_unregistered_email_is_refused(platform_admin) -> None:  # type: ignore[no-untyped-def]
    """No auto-create: registering an account and handing it the top privilege in one
    unreviewed step is exactly what this refusal prevents."""
    client, _ = platform_admin

    response = client.post(GRANT, {"email": "ghost@example.com"})

    assert response.status_code == 200
    assert "No registered user with that email." in response.content.decode()


@pytest.mark.django_db
def test_revoking_removes_them_from_the_tier(platform_admin) -> None:  # type: ignore[no-untyped-def]
    client, _ = platform_admin
    other = _global_admin(f"{ADMIN_MARKER}-2@example.com")

    client.post(REVOKE, {"user_id": other.pk}, follow=True)

    assert other.email not in client.get(PAGE).content.decode()


@pytest.mark.django_db
def test_revoking_also_demotes_them_in_normal_orgs(platform_admin) -> None:  # type: ignore[no-untyped-def]
    # The decided semantics (Story 13.1): revoke the elevated access fully, rather than
    # leaving them an admin of every org they were auto-provisioned into.
    client, _ = platform_admin
    other = _global_admin(f"{ADMIN_MARKER}-2@example.com")
    acme = OrgMembership.objects.filter(org__name="Acme").first().org
    assert OrgMembership.objects.get(org=acme, user=other).role == OrgMembership.Role.ADMIN

    client.post(REVOKE, {"user_id": other.pk})

    assert OrgMembership.objects.get(org=acme, user=other).role == OrgMembership.Role.MEMBER


# --- AC #3: the tier can never be emptied -------------------------------------------------


@pytest.mark.django_db
def test_the_last_global_admin_cannot_revoke_themselves(platform_admin) -> None:  # type: ignore[no-untyped-def]
    client, user = platform_admin

    response = client.post(REVOKE, {"user_id": user.pk}, follow=True)

    assert "at least one global admin" in response.content.decode()
    assert user.email in client.get(PAGE).content.decode()


@pytest.mark.django_db
def test_self_revocation_is_allowed_when_someone_else_remains(platform_admin) -> None:  # type: ignore[no-untyped-def]
    """Only the *last* global admin is blocked — the Dev Notes call this out explicitly."""
    client, user = platform_admin
    _global_admin(f"{ADMIN_MARKER}-2@example.com")

    client.post(REVOKE, {"user_id": user.pk})

    # The tier itself changed; the page stays reachable, because Story 21.24 removed the
    # gate that used to make revocation a self-lockout.
    assert is_global_admin(user) is False
    assert client.get(PAGE).status_code == 200


@pytest.mark.django_db
def test_revoking_someone_who_is_not_on_the_tier_is_reported_plainly(platform_admin) -> None:  # type: ignore[no-untyped-def]
    client, _ = platform_admin
    ordinary = register_user(email="ordinary@example.com", password=PASSWORD)

    response = client.post(REVOKE, {"user_id": ordinary.pk}, follow=True)

    assert "not a global admin" in response.content.decode()


# --- AC #2 + #5: the denial matrix --------------------------------------------------------


@pytest.mark.django_db
def test_the_admin_org_never_becomes_the_active_workspace(member_client: Client) -> None:
    """Story 2.18: the ADMIN org is a platform tier, not a workspace.

    That rule outlived the access control Story 21.24 deleted — it is about which org a
    request *acts as*, not about who is asking. Pinning the ADMIN org in the session by hand
    must still not make it the acting org, or every org-scoped page would start writing into
    the meta org.
    """
    from inventory.users.models import Org

    admin_org = Org.objects.get(is_admin_org=True)
    session = member_client.session
    session["active_org_id"] = admin_org.pk
    session.save()

    member_client.get(PAGE)
    resolved = _resolved_org(member_client)

    assert resolved is not None
    assert resolved.is_admin_org is False


# --- AC #4 + hardening ---------------------------------------------------------------------


@pytest.mark.django_db
def test_revoke_carries_a_confirmation(platform_admin) -> None:  # type: ignore[no-untyped-def]
    client, _ = platform_admin
    assert "confirm(" in client.get(PAGE).content.decode()


@pytest.mark.django_db
def test_mutations_reject_get_and_require_csrf(platform_admin) -> None:  # type: ignore[no-untyped-def]
    client, _ = platform_admin
    for url in (GRANT, REVOKE):
        assert client.get(url).status_code == 405, url

    strict = Client(enforce_csrf_checks=True)
    assert strict.login(email=f"{ADMIN_MARKER}-1@example.com", password=PASSWORD)
    for url in (GRANT, REVOKE):
        assert strict.post(url, {}).status_code == 403, url


@pytest.mark.django_db
def test_the_page_posts_to_the_html_routes_not_the_json_api(platform_admin) -> None:  # type: ignore[no-untyped-def]
    client, _ = platform_admin
    html = client.get(PAGE).content.decode()
    assert f'action="{GRANT}"' in html
    assert f'action="{REVOKE}"' in html
    assert "/api/v1/admin/" not in html
