"""The Organization page (Story 21.6, trimmed by Story 22.9).

This module used to cover the members roster and its six mutations as well. Story 22.9 deleted
that UI: with no identity, membership records gate nothing, and every mutation was either
meaningless or outright broken for the anonymous caller that is now the ordinary one
(`POST /organization/leave` raised `TypeError` on `AnonymousUser`).

**No rule coverage was lost.** The membership *business* rules — last admin cannot be demoted,
a global admin cannot be removed from a normal org, the sole admin cannot leave, the last
member of the ADMIN org is protected — live in `inventory.users.services` and are exercised
through the API by `tests/unit/test_membership.py`, which covers them more thoroughly (27
tests) than the page module did. Deleting page tests removed a second, weaker view of the same
services, not the assertions themselves.

What remains here is the organization surface that is still real: the hub, and creating an org.
"""

from __future__ import annotations

import pytest
from django.test import Client

from inventory.users.models import Org, OrgMembership
from inventory.users.services import create_org, register_user

HUB = "/organization"
ORG_CREATE = "/organization/create"
PASSWORD = "pw12345678"


def _user(email: str) -> object:
    return register_user(email=email, password=PASSWORD)


def _client(email: str) -> Client:
    client = Client()
    assert client.login(email=email, password=PASSWORD)
    return client


# --- The hub ------------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_hub_shows_the_active_org_and_links_to_keys() -> None:
    """Composition by linking (Story 2.11): the hub points at surfaces, it does not inline them."""
    user = _user("admin@example.com")
    org = create_org(name="Acme", admin_user=user)

    html = _client("admin@example.com").get(HUB).content.decode()

    assert org.name in html
    assert 'href="/keys"' in html


@pytest.mark.django_db
def test_the_hub_no_longer_offers_member_management() -> None:
    """Story 22.9 removed that surface; a dead link here would be worse than no link."""
    create_org(name="Acme", admin_user=_user("admin@example.com"))

    html = _client("admin@example.com").get(HUB).content.decode()

    assert "/members" not in html
    assert "/organization/leave" not in html


# --- Creating an org ------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_signed_in_user_creates_an_org_and_becomes_its_admin() -> None:
    """Was "global admins only" (Story 2.12) until Story 21.24 removed the gate."""
    root = _user("root@example.com")
    create_org(name="Home", admin_user=root)
    client = _client("root@example.com")

    assert ORG_CREATE in client.get(HUB).content.decode()
    response = client.post(ORG_CREATE, {"name": "Fresh Org"})

    assert response.status_code == 302
    org = Org.objects.get(name="Fresh Org")
    assert OrgMembership.objects.get(org=org, user=root).role == OrgMembership.Role.ADMIN


@pytest.mark.django_db
def test_creating_an_org_switches_you_into_it() -> None:
    """Landing in the thing you just made, rather than whichever org happened to be active."""
    root = _user("root@example.com")
    create_org(name="Home", admin_user=root)
    client = _client("root@example.com")

    client.post(ORG_CREATE, {"name": "Second Org"})

    assert "Second Org" in client.get(HUB).content.decode()
