"""Tests for org administration and membership management (Story 2.3)."""

import pytest
from rest_framework.test import APIClient

from generate_sbom.users.models import OrgMembership, User
from generate_sbom.users.services import create_org, register_user

LAST_ADMIN_ERROR = "An org must always have at least one admin."


def _register_with_org(email: str, org_name: str, password: str = "pw12345678") -> User:
    """Register a user and give them a first org (registration now creates none)."""
    user = register_user(email=email, password=password)
    create_org(name=org_name, admin_user=user)
    return user


def _client(email: str, password: str = "pw12345678") -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
    return client


def _add_member(client: APIClient, email: str, temp_password: str = "temp12345") -> User:
    client.post(
        "/api/v1/orgs/members/",
        {"email": email, "temp_password": temp_password},
        format="json",
    )
    return User.objects.get(email=email)


@pytest.mark.django_db
def test_create_org_adds_caller_as_admin() -> None:
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/create/", {"name": "New Team"}, format="json")

    assert response.status_code == 201
    assert response.data["slug"] == "new-team"
    alice = User.objects.get(email="alice@example.com")
    assert OrgMembership.objects.filter(org__slug="new-team", user=alice, role="admin").exists()


@pytest.mark.django_db
def test_add_member_creates_membership_without_email(mailoutbox: list) -> None:
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")

    bob = _add_member(client, "bob@example.com")

    assert OrgMembership.objects.filter(org__slug="alice", user=bob, role="member").exists()
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_add_existing_member_rejected() -> None:
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")
    _add_member(client, "bob@example.com")

    response = client.post(
        "/api/v1/orgs/members/",
        {"email": "bob@example.com", "temp_password": "temp12345"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "already_member"


@pytest.mark.django_db
def test_remove_member() -> None:
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")
    bob = _add_member(client, "bob@example.com")

    response = client.delete(f"/api/v1/orgs/members/{bob.pk}/")

    assert response.status_code == 204
    assert not OrgMembership.objects.filter(org__slug="alice", user=bob).exists()


@pytest.mark.django_db
def test_remove_sole_admin_rejected() -> None:
    alice = _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")

    response = client.delete(f"/api/v1/orgs/members/{alice.pk}/")

    assert response.status_code == 400
    assert response.data["code"] == "last_admin"
    assert response.data["error"] == LAST_ADMIN_ERROR


@pytest.mark.django_db
def test_transfer_admin_promotes_and_demotes_sole_admin() -> None:
    alice = _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")
    bob = _add_member(client, "bob@example.com")

    response = client.post("/api/v1/orgs/transfer-admin/", {"user_id": bob.pk}, format="json")

    assert response.status_code == 200
    assert OrgMembership.objects.get(org__slug="alice", user=bob).role == "admin"
    assert OrgMembership.objects.get(org__slug="alice", user=alice).role == "member"


@pytest.mark.django_db
def test_non_sole_admin_can_leave() -> None:
    _register_with_org("alice@example.com", "Alice")
    admin_client = _client("alice@example.com")
    bob = _add_member(admin_client, "bob@example.com")

    bob_client = _client("bob@example.com", "temp12345")
    response = bob_client.post("/api/v1/orgs/leave/")

    assert response.status_code == 204
    assert not OrgMembership.objects.filter(org__slug="alice", user=bob).exists()


@pytest.mark.django_db
def test_sole_admin_cannot_leave() -> None:
    _register_with_org("alice@example.com", "Alice")
    client = _client("alice@example.com")

    response = client.post("/api/v1/orgs/leave/")

    assert response.status_code == 400
    assert response.data["code"] == "last_admin"


@pytest.mark.django_db
def test_list_members_is_org_scoped_and_flags_admin() -> None:
    _register_with_org("alice@example.com", "Alice")
    _register_with_org("carol@example.com", "Carol")  # separate org
    client = _client("alice@example.com")
    _add_member(client, "bob@example.com")

    response = client.get("/api/v1/orgs/members/")

    assert response.status_code == 200
    emails = {m["email"] for m in response.data["members"]}
    assert emails == {"alice@example.com", "bob@example.com"}
    assert response.data["is_admin"] is True


@pytest.mark.django_db
def test_non_admin_blocked_from_admin_actions() -> None:
    _register_with_org("alice@example.com", "Alice")
    admin_client = _client("alice@example.com")
    _add_member(admin_client, "bob@example.com")

    bob_client = _client("bob@example.com", "temp12345")
    add = bob_client.post(
        "/api/v1/orgs/members/",
        {"email": "eve@example.com", "temp_password": "temp12345"},
        format="json",
    )
    roster = bob_client.get("/api/v1/orgs/members/")

    assert add.status_code == 403
    assert add.data["code"] == "not_admin"
    assert roster.data["is_admin"] is False
