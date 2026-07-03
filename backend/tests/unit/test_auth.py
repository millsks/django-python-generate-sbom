"""Tests for session login/logout (Story 2.2)."""

import pytest
from rest_framework.test import APIClient

from generate_sbom.users.auth import SESSION_ACTIVE_ORG
from generate_sbom.users.services import register_user


@pytest.mark.django_db
def test_login_success_creates_session_and_active_org() -> None:
    """Valid credentials create a session and pin the personal org as active."""
    register_user(email="alice@example.com", password="pw12345678")
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {"email": "alice@example.com", "password": "pw12345678"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["org"]["slug"] == "alice"
    assert "_auth_user_id" in client.session
    assert client.session[SESSION_ACTIVE_ORG] is not None


@pytest.mark.django_db
def test_login_wrong_password_is_generic() -> None:
    """A wrong password returns the generic message with no field hint."""
    register_user(email="alice@example.com", password="pw12345678")
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {"email": "alice@example.com", "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401
    assert response.data["error"] == "Invalid email or password"


@pytest.mark.django_db
def test_login_unknown_email_is_generic() -> None:
    """An unknown email returns the same generic message (no user enumeration)."""
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {"email": "nobody@example.com", "password": "whatever12"},
        format="json",
    )

    assert response.status_code == 401
    assert response.data["error"] == "Invalid email or password"


@pytest.mark.django_db
def test_login_missing_fields_is_generic() -> None:
    """A malformed login body returns the generic credential message."""
    client = APIClient()

    response = client.post("/api/v1/auth/login/", {"email": "a@b.com"}, format="json")

    assert response.status_code == 400
    assert response.data["error"] == "Invalid email or password"


@pytest.mark.django_db
def test_logout_invalidates_session() -> None:
    """Logout clears the authenticated session."""
    register_user(email="alice@example.com", password="pw12345678")
    client = APIClient()
    client.post(
        "/api/v1/auth/login/",
        {"email": "alice@example.com", "password": "pw12345678"},
        format="json",
    )
    assert "_auth_user_id" in client.session

    response = client.post("/api/v1/auth/logout/")

    assert response.status_code == 204
    assert "_auth_user_id" not in client.session
