"""Tests for session login/logout (Story 2.2)."""

import pytest
from rest_framework.test import APIClient

from generate_sbom.users.auth import SESSION_ACTIVE_ORG
from generate_sbom.users.models import User
from generate_sbom.users.services import create_org, get_the_admin_org, register_user


@pytest.mark.django_db
def test_login_success_creates_session_and_active_org() -> None:
    """Valid credentials create a session and pin the user's org as active."""
    user = register_user(email="alice@example.com", password="pw12345678")
    create_org(name="Alice", admin_user=user)
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
def test_login_zero_org_user_stays_authenticated() -> None:
    """A zero-org user logs in successfully with ``org: null`` (Story 2.6)."""
    register_user(email="alice@example.com", password="pw12345678")
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {"email": "alice@example.com", "password": "pw12345678"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["org"] is None
    assert "_auth_user_id" in client.session
    assert SESSION_ACTIVE_ORG not in client.session


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


# --- Story 2.18: the ADMIN org is never the active working org -------------


@pytest.mark.django_db
def test_admin_org_never_active_via_session_path() -> None:
    """A pinned ADMIN ``active_org_id`` resolves to no active org (session path, Story 2.18)."""
    User.objects.create_superuser(email="root@example.com", password="pw12345678")
    admin_org = get_the_admin_org()
    assert admin_org is not None
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": "root@example.com", "password": "pw12345678"}, format="json")
    session = client.session
    session[SESSION_ACTIVE_ORG] = admin_org.pk
    session.save()

    response = client.get("/api/v1/orgs/me/")

    assert response.status_code == 404
    assert response.data["code"] == "no_active_org"


@pytest.mark.django_db
def test_admin_org_never_active_via_fallback_path() -> None:
    """A user whose only membership is the ADMIN org resolves to no active org (fallback)."""
    User.objects.create_superuser(email="root@example.com", password="pw12345678")
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": "root@example.com", "password": "pw12345678"}, format="json")
    # Clear any pinned org so resolution goes through the fallback branch.
    session = client.session
    session.pop(SESSION_ACTIVE_ORG, None)
    session.save()

    response = client.get("/api/v1/orgs/me/")

    assert response.status_code == 404
    assert response.data["code"] == "no_active_org"


@pytest.mark.django_db
def test_org_scoped_endpoint_denies_with_no_active_org() -> None:
    """An org-scoped endpoint denies a zero-org user (defense in depth, Story 2.18)."""
    register_user(email="alice@example.com", password="pw12345678")
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": "pw12345678"}, format="json")

    response = client.get("/api/v1/keys/")

    assert response.status_code == 404
    assert response.data["code"] == "no_active_org"


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
