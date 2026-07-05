"""Tests for zero-org registration and the auth/me identity endpoint (Story 2.6)."""

import pytest
from django.db import IntegrityError
from rest_framework.test import APIClient

from generate_sbom.users.models import Org, User
from generate_sbom.users.services import register_user


@pytest.mark.django_db
def test_register_user_creates_user_with_zero_orgs() -> None:
    """Registration creates the user only — no personal org (Story 2.6, AC #1)."""
    user = register_user(email="alice@example.com", password="pw12345678")

    assert user.org_memberships.count() == 0
    # Only the seeded ADMIN org exists; registration creates no member org.
    assert Org.objects.filter(is_admin_org=False).count() == 0


@pytest.mark.django_db
def test_register_duplicate_email_rolls_back() -> None:
    """A duplicate email raises and leaves exactly one User and zero orgs (AC #2)."""
    register_user(email="alice@example.com", password="pw12345678")
    with pytest.raises(IntegrityError):
        register_user(email="alice@example.com", password="pw12345678")

    assert User.objects.count() == 1
    assert Org.objects.filter(is_admin_org=False).count() == 0


@pytest.mark.django_db
def test_register_api_creates_account_with_null_org() -> None:
    """POST /api/v1/auth/register/ returns 201 with the user and ``org: null``."""
    response = APIClient().post(
        "/api/v1/auth/register/",
        {"email": "bob@example.com", "password": "pw12345678"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["user"]["email"] == "bob@example.com"
    assert isinstance(response.data["user"]["id"], int)
    assert response.data["org"] is None


@pytest.mark.django_db
def test_register_api_duplicate_returns_400_envelope() -> None:
    """A duplicate registration returns 400 with the standard error envelope."""
    client = APIClient()
    payload = {"email": "bob@example.com", "password": "pw12345678"}
    client.post("/api/v1/auth/register/", payload, format="json")
    response = client.post("/api/v1/auth/register/", payload, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"


@pytest.mark.django_db
def test_auth_me_returns_identity_for_zero_org_user() -> None:
    """GET /api/v1/auth/me/ returns id+email for a zero-org authenticated user."""
    user = register_user(email="alice@example.com", password="pw12345678")
    client = APIClient()
    client.post(
        "/api/v1/auth/login/",
        {"email": "alice@example.com", "password": "pw12345678"},
        format="json",
    )

    response = client.get("/api/v1/auth/me/")

    assert response.status_code == 200
    assert response.data == {"id": user.pk, "email": "alice@example.com"}


@pytest.mark.django_db
def test_auth_me_requires_authentication() -> None:
    """An unauthenticated GET /api/v1/auth/me/ is rejected (not logged in).

    The project's default auth stack leads with the Api-Key authenticator, which
    sets a WWW-Authenticate header, so DRF renders the rejection as 401; a
    session-only stack would render 403. Either way the SPA reads it as anon,
    matching ``test_orgs_require_authentication``.
    """
    response = APIClient().get("/api/v1/auth/me/")
    assert response.status_code in (401, 403)
