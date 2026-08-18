"""Tests for org listing and switching (Story 2.2, FR-1.6)."""

import pytest
from rest_framework.test import APIClient

from django_service.users.models import User
from inventory.users.auth import SESSION_ACTIVE_ORG
from inventory.users.services import create_org, register_user


def _login(client: APIClient, email: str, password: str) -> None:
    # Story 21.24 deleted POST /api/v1/auth/login/. Django's session login still works
    # (the user model and SessionAuthentication both survive), so these tests keep
    # exercising a real principal rather than the anonymous default-org path.
    client.login(email=email, password=password)


def _register_with_org(email: str, org_name: str, password: str = "pw12345678") -> User:
    """Register a user and give them a first org (registration now creates none)."""
    user = register_user(email=email, password=password)
    create_org(name=org_name, admin_user=user)
    return user


@pytest.mark.django_db
def test_org_list_flags_exactly_one_active() -> None:
    """The org list returns every switchable org with exactly one flagged active.

    Story 21.24 removed the membership filter — there is no membership left to filter by —
    so the seeded default org appears alongside the user's own. The invariant that still
    matters is that **exactly one** is flagged active.
    """
    from django.conf import settings

    user = _register_with_org("alice@example.com", "Alice")
    create_org(name="Second", admin_user=user)
    client = APIClient()
    _login(client, "alice@example.com", "pw12345678")

    response = client.get("/api/v1/orgs/")

    assert response.status_code == 200
    assert {o["slug"] for o in response.data} == {"alice", "second", settings.INVENTORY_DEFAULT_ORG_SLUG}
    assert sum(1 for o in response.data if o["active"]) == 1


@pytest.mark.django_db
def test_switch_to_member_org_updates_active() -> None:
    """Switching to an org the user belongs to updates the active org."""
    user = _register_with_org("alice@example.com", "Alice")
    create_org(name="Second", admin_user=user)
    client = APIClient()
    _login(client, "alice@example.com", "pw12345678")

    switch = client.post("/api/v1/orgs/switch/", {"slug": "second"}, format="json")
    assert switch.status_code == 200
    assert switch.data["slug"] == "second"

    me = client.get("/api/v1/orgs/me/")
    assert me.data["slug"] == "second"


@pytest.mark.django_db
def test_session_request_resolves_active_org() -> None:
    """A session-authenticated request (no Api-Key) resolves the active org."""
    _register_with_org("alice@example.com", "Alice")
    client = APIClient()
    _login(client, "alice@example.com", "pw12345678")

    response = client.get("/api/v1/orgs/me/")

    assert response.status_code == 200
    assert response.data["slug"] == "alice"


@pytest.mark.django_db
def test_active_org_falls_back_to_membership() -> None:
    """With no active org in the session, resolution falls back to a membership.

    Django's session login (Story 21.24 deleted the DRF login endpoint) does not pin an
    active org, so the session simply starts without one — which is exactly the state this
    test wants, and is why nothing is deleted from it first.
    """
    _register_with_org("alice@example.com", "Alice")
    client = APIClient()
    _login(client, "alice@example.com", "pw12345678")
    assert SESSION_ACTIVE_ORG not in client.session

    response = client.get("/api/v1/orgs/me/")

    assert response.status_code == 200
    assert response.data["slug"] == "alice"
