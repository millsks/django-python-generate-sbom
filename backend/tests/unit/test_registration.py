"""Tests for the registration service and endpoint (Story 2.1, FR-1.1)."""

import pytest
from django.db import IntegrityError
from rest_framework.test import APIClient

from generate_sbom.users.models import Org, OrgMembership, User
from generate_sbom.users.services import register_user


@pytest.mark.django_db
def test_register_user_creates_user_org_and_admin_membership() -> None:
    """Registration creates the user, a personal org, and an admin membership."""
    user = register_user(email="alice@example.com", password="pw12345678")

    membership = user.org_memberships.get()
    assert membership.role == OrgMembership.Role.ADMIN
    assert membership.org.name == "alice"
    assert membership.org.slug == "alice"


@pytest.mark.django_db
def test_register_duplicate_email_rolls_back() -> None:
    """A duplicate email raises and leaves zero new User/Org rows (AC #2)."""
    register_user(email="alice@example.com", password="pw12345678")
    with pytest.raises(IntegrityError):
        register_user(email="alice@example.com", password="pw12345678")

    assert User.objects.count() == 1
    assert Org.objects.count() == 1


@pytest.mark.django_db
def test_register_api_creates_account() -> None:
    """POST /api/v1/auth/register/ returns 201 with the user and org summary."""
    response = APIClient().post(
        "/api/v1/auth/register/",
        {"email": "bob@example.com", "password": "pw12345678"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["user"]["email"] == "bob@example.com"
    assert response.data["org"]["slug"] == "bob"


@pytest.mark.django_db
def test_register_api_duplicate_returns_400_envelope() -> None:
    """A duplicate registration returns 400 with the standard error envelope."""
    client = APIClient()
    payload = {"email": "bob@example.com", "password": "pw12345678"}
    client.post("/api/v1/auth/register/", payload, format="json")
    response = client.post("/api/v1/auth/register/", payload, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
