"""Tests for org listing and switching (Story 2.2, FR-1.6)."""

import pytest
from rest_framework.test import APIClient

from generate_sbom.users.auth import SESSION_ACTIVE_ORG
from generate_sbom.users.models import User
from generate_sbom.users.services import create_org, register_user


def _login(client: APIClient, email: str, password: str) -> None:
    client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")


def _register_with_org(email: str, org_name: str, password: str = "pw12345678") -> User:
    """Register a user and give them a first org (registration now creates none)."""
    user = register_user(email=email, password=password)
    create_org(name=org_name, admin_user=user)
    return user


@pytest.mark.django_db
def test_org_list_flags_exactly_one_active() -> None:
    """The org list returns all memberships with exactly one flagged active."""
    user = _register_with_org("alice@example.com", "Alice")
    create_org(name="Second", admin_user=user)
    client = APIClient()
    _login(client, "alice@example.com", "pw12345678")

    response = client.get("/api/v1/orgs/")

    assert response.status_code == 200
    assert {o["slug"] for o in response.data} == {"alice", "second"}
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
def test_switch_to_non_member_org_rejected() -> None:
    """Switching to an org the user does not belong to is rejected."""
    _register_with_org("alice@example.com", "Alice")
    _register_with_org("bob@example.com", "Bob")
    client = APIClient()
    _login(client, "alice@example.com", "pw12345678")

    response = client.post("/api/v1/orgs/switch/", {"slug": "bob"}, format="json")

    assert response.status_code == 403
    assert response.data["code"] == "not_a_member"


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
    """With no active org in the session, resolution falls back to a membership."""
    _register_with_org("alice@example.com", "Alice")
    client = APIClient()
    _login(client, "alice@example.com", "pw12345678")
    session = client.session
    del session[SESSION_ACTIVE_ORG]
    session.save()

    response = client.get("/api/v1/orgs/me/")

    assert response.status_code == 200
    assert response.data["slug"] == "alice"


@pytest.mark.django_db
def test_orgs_require_authentication() -> None:
    """Org endpoints reject unauthenticated requests."""
    response = APIClient().get("/api/v1/orgs/")
    assert response.status_code in (401, 403)
