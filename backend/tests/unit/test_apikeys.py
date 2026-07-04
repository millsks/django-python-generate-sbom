"""Tests for API key management and the Api-Key auth class (Story 2.4)."""

import pytest
from rest_framework.test import APIClient

from generate_sbom.users.models import OrgApiKey
from generate_sbom.users.services import register_user


def _login(email: str, password: str = "pw12345678") -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
    return client


@pytest.mark.django_db
def test_create_key_returns_plaintext_once_and_list_hides_it() -> None:
    register_user(email="alice@example.com", password="pw12345678")
    client = _login("alice@example.com")

    created = client.post("/api/v1/keys/", {"name": "ci"}, format="json")
    assert created.status_code == 201
    assert len(created.data["key"]) > 10  # plaintext shown once

    listed = client.get("/api/v1/keys/")
    assert listed.status_code == 200
    row = listed.data[0]
    assert row["name"] == "ci"
    assert "prefix" in row
    assert "key" not in row
    assert "hashed_key" not in row


@pytest.mark.django_db
def test_eleventh_active_key_rejected() -> None:
    register_user(email="alice@example.com", password="pw12345678")
    client = _login("alice@example.com")
    for i in range(10):
        client.post("/api/v1/keys/", {"name": f"k{i}"}, format="json")

    response = client.post("/api/v1/keys/", {"name": "k10"}, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "api_key_limit_reached"
    assert response.data["error"] == "This org has reached the maximum of 10 active API keys."


@pytest.mark.django_db
def test_valid_key_authenticates_and_updates_last_used() -> None:
    register_user(email="alice@example.com", password="pw12345678")
    admin = _login("alice@example.com")
    key = admin.post("/api/v1/keys/", {"name": "ci"}, format="json").data["key"]

    response = APIClient().get("/api/v1/keys/", HTTP_AUTHORIZATION=f"Api-Key {key}")

    assert response.status_code == 200
    assert OrgApiKey.objects.get(name="ci").last_used_at is not None


@pytest.mark.django_db
def test_revoked_key_is_rejected() -> None:
    register_user(email="alice@example.com", password="pw12345678")
    admin = _login("alice@example.com")
    created = admin.post("/api/v1/keys/", {"name": "ci"}, format="json")
    key, key_id = created.data["key"], created.data["id"]

    assert admin.delete(f"/api/v1/keys/{key_id}/").status_code == 204

    response = APIClient().get("/api/v1/keys/", HTTP_AUTHORIZATION=f"Api-Key {key}")
    assert response.status_code == 401
    assert response.data["code"] == "invalid_api_key"


@pytest.mark.django_db
def test_bogus_key_is_rejected() -> None:
    response = APIClient().get("/api/v1/keys/", HTTP_AUTHORIZATION="Api-Key not.arealkey")
    assert response.status_code == 401
    assert response.data["code"] == "invalid_api_key"


@pytest.mark.django_db
def test_revoke_other_orgs_key_returns_404() -> None:
    register_user(email="alice@example.com", password="pw12345678")
    register_user(email="bob@example.com", password="pw12345678")
    bob_key_id = _login("bob@example.com").post("/api/v1/keys/", {"name": "bobkey"}, format="json").data["id"]

    response = _login("alice@example.com").delete(f"/api/v1/keys/{bob_key_id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_non_admin_cannot_create_key() -> None:
    register_user(email="alice@example.com", password="pw12345678")
    admin = _login("alice@example.com")
    admin.post(
        "/api/v1/orgs/members/",
        {"email": "bob@example.com", "temp_password": "temp12345"},
        format="json",
    )

    response = _login("bob@example.com", "temp12345").post("/api/v1/keys/", {"name": "x"}, format="json")

    assert response.status_code == 403
    assert response.data["code"] == "not_admin"
