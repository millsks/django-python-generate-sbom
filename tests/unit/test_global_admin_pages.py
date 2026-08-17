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

from inventory.users.models import OrgMembership
from inventory.users.services import create_member, create_org, grant_global_admin, register_user

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

    # Having just revoked their own flag, the page is no longer theirs to see.
    assert client.get(PAGE).status_code == 403


@pytest.mark.django_db
def test_revoking_someone_who_is_not_on_the_tier_is_reported_plainly(platform_admin) -> None:  # type: ignore[no-untyped-def]
    client, _ = platform_admin
    ordinary = register_user(email="ordinary@example.com", password=PASSWORD)

    response = client.post(REVOKE, {"user_id": ordinary.pk}, follow=True)

    assert "not a global admin" in response.content.decode()


# --- AC #2 + #5: the denial matrix --------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("url", ALL_URLS)
def test_anonymous_is_redirected_and_sees_nothing(url: str) -> None:
    _global_admin(f"{ADMIN_MARKER}-1@example.com")

    response = Client().post(url, {})

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")

    # A 302 has an empty body, so checking it for a leak proves nothing. Follow the redirect
    # and check the page the caller actually lands on.
    landed = Client().post(url, {}, follow=True)
    assert ADMIN_MARKER not in landed.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("url", ALL_URLS)
def test_a_plain_member_is_forbidden_and_sees_no_admin_email(member_client: Client, url: str) -> None:
    response = member_client.post(url, {})

    assert response.status_code == 403
    # The status alone is not enough: a 403 that still rendered the roster would leak the tier.
    assert ADMIN_MARKER not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("url", ALL_URLS)
def test_an_org_admin_is_forbidden_and_sees_no_admin_email(org_admin_client: Client, url: str) -> None:
    """Being an admin of a normal org is not the platform tier — the privilege boundary."""
    response = org_admin_client.post(url, {})

    assert response.status_code == 403
    assert ADMIN_MARKER not in response.content.decode()


@pytest.mark.django_db
def test_an_org_admin_cannot_grant_themselves_the_flag(org_admin_client: Client) -> None:
    # The escalation this page must not permit.
    response = org_admin_client.post(GRANT, {"email": "org-admin@example.com"})

    assert response.status_code == 403
    admin = OrgMembership.objects.filter(user__email="org-admin@example.com", org__is_admin_org=True)
    assert not admin.exists()


@pytest.mark.django_db
def test_switching_into_the_admin_org_does_not_open_the_page(member_client: Client) -> None:
    """Story 2.18: the ADMIN org is not a workspace, so it cannot be used as a way in."""
    from inventory.users.models import Org

    admin_org = Org.objects.get(is_admin_org=True)
    session = member_client.session
    session["active_org_id"] = admin_org.pk
    session.save()

    response = member_client.get(PAGE)

    assert response.status_code == 403
    assert ADMIN_MARKER not in response.content.decode()


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
