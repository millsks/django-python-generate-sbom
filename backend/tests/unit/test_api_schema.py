"""Tests for the OpenAPI schema + Swagger UI/ReDoc endpoints (Story 11.9)."""

import importlib

from django.test import Client, override_settings
from django.urls import clear_url_caches


def test_schema_endpoint_returns_valid_openapi_document() -> None:
    """GET /api/schema/?format=json returns 200 with a valid OpenAPI 3 document."""
    response = Client().get("/api/schema/", {"format": "json"})

    assert response.status_code == 200
    schema = response.json()
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "generate-sbom API"
    assert schema["paths"]


def test_schema_declares_the_org_api_key_security_scheme() -> None:
    """The custom Api-Key auth surfaces as an apiKey security scheme (extension)."""
    schema = Client().get("/api/schema/", {"format": "json"}).json()

    schemes = schema["components"]["securitySchemes"]
    assert "OrgApiKey" in schemes
    assert schemes["OrgApiKey"] == {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Organization API key. Send as `Authorization: Api-Key <key>`.",
    }


def test_swagger_ui_endpoint_renders_without_auth() -> None:
    """GET /api/docs/ returns 200 HTML (self-hosted Swagger UI, no auth required)."""
    response = Client().get("/api/docs/")

    assert response.status_code == 200
    assert b"swagger" in response.content.lower()


def test_redoc_endpoint_renders_without_auth() -> None:
    """GET /api/redoc/ returns 200 HTML."""
    response = Client().get("/api/redoc/")

    assert response.status_code == 200
    assert b"redoc" in response.content.lower()


def test_docs_endpoints_are_disabled_when_api_docs_disabled() -> None:
    """With API_DOCS_ENABLED=False the doc routes are not registered (404)."""
    import config.urls

    with override_settings(API_DOCS_ENABLED=False):
        clear_url_caches()
        importlib.reload(config.urls)
        try:
            assert Client().get("/api/schema/").status_code == 404
            assert Client().get("/api/docs/").status_code == 404
        finally:
            # Restore the enabled URLconf for subsequent tests.
            clear_url_caches()
            importlib.reload(config.urls)
