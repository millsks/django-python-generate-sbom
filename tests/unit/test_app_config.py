"""Tests for the public app-config endpoint (Story 11.20)."""

from django.test import Client, override_settings


def test_config_endpoint_returns_flag_without_auth() -> None:
    """GET /api/v1/config/ returns 200 with api_docs_enabled and needs no auth."""
    response = Client().get("/api/v1/config/")

    assert response.status_code == 200
    assert set(response.json()) == {"api_docs_enabled"}


@override_settings(API_DOCS_ENABLED=True)
def test_config_reflects_api_docs_enabled_true() -> None:
    """The flag mirrors settings.API_DOCS_ENABLED when it is on."""
    response = Client().get("/api/v1/config/")

    assert response.status_code == 200
    assert response.json() == {"api_docs_enabled": True}


@override_settings(API_DOCS_ENABLED=False)
def test_config_reflects_api_docs_enabled_false() -> None:
    """The flag mirrors settings.API_DOCS_ENABLED when it is off."""
    response = Client().get("/api/v1/config/")

    assert response.status_code == 200
    assert response.json() == {"api_docs_enabled": False}
