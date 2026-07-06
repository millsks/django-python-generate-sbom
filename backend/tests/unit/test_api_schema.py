"""Tests for the OpenAPI schema + Swagger UI/ReDoc endpoints (Story 11.9)."""

import importlib
from typing import Any

import pytest
from django.test import Client, override_settings
from django.urls import clear_url_caches


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    """The generated OpenAPI document, fetched in-process (no live server)."""
    document: dict[str, Any] = Client().get("/api/schema/", {"format": "json"}).json()
    return document


def _param_names(operation: dict[str, Any], location: str) -> set[str]:
    """Return the declared parameter names for the given ``in`` location."""
    return {p["name"] for p in operation.get("parameters", []) if p["in"] == location}


def _resolve(schema: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    """Resolve a ``$ref`` node against ``components/schemas`` (one hop)."""
    ref = node.get("$ref")
    if ref is None:
        return node
    name = ref.rsplit("/", 1)[-1]
    resolved: dict[str, Any] = schema["components"]["schemas"][name]
    return resolved


def _request_properties(schema: dict[str, Any], path: str, media_type: str) -> dict[str, Any]:
    """Return the property map of a POST requestBody for the given media type."""
    node = schema["paths"][path]["post"]["requestBody"]["content"][media_type]["schema"]
    properties: dict[str, Any] = _resolve(schema, node)["properties"]
    return properties


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


def test_api_docs_enabled_by_default() -> None:
    """API_DOCS_ENABLED defaults to True (docs enabled) when the env var is unset."""
    from django.conf import settings

    assert settings.API_DOCS_ENABLED is True


# --- Story 11.19: schema completeness (request bodies + parameters) ---


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/orgs/switch/",
        "/api/v1/sbom/jobs/artifacts/bulk-delete/",
        "/api/v1/sbom/generate/",
        "/api/v1/manifests/upload/",
    ],
)
def test_previously_missing_post_endpoints_declare_a_request_body(schema: dict[str, Any], path: str) -> None:
    """The formerly serializer-less / manual-serializer POSTs now expose a requestBody."""
    operation = schema["paths"][path]["post"]

    assert "requestBody" in operation
    assert operation["requestBody"]["content"], "requestBody exposes no media type / fields"


@pytest.mark.parametrize("path", ["/api/v1/sbom/generate/", "/api/v1/manifests/upload/"])
def test_file_upload_endpoints_declare_multipart_request_body(schema: dict[str, Any], path: str) -> None:
    """The manifest/SBOM upload POSTs declare a multipart/form-data body with the file field."""
    content = schema["paths"][path]["post"]["requestBody"]["content"]

    assert "multipart/form-data" in content
    assert "file" in _request_properties(schema, path, "multipart/form-data")


def test_jobs_list_declares_status_and_format_query_parameters(schema: dict[str, Any]) -> None:
    """GET /sbom/jobs/ declares the custom ``status`` and ``format`` query filters."""
    query_params = _param_names(schema["paths"]["/api/v1/sbom/jobs/"]["get"], "query")

    assert {"status", "format"} <= query_params


def test_parameterized_get_declares_its_path_parameter(schema: dict[str, Any]) -> None:
    """A representative parameterized GET declares its ``task_id`` path parameter."""
    path_params = _param_names(schema["paths"]["/api/v1/sbom/status/{task_id}/"]["get"], "path")

    assert "task_id" in path_params


def test_org_switch_request_body_exposes_the_slug_field(schema: dict[str, Any]) -> None:
    """The authored OrgSwitch request serializer surfaces its ``slug`` field."""
    assert "slug" in _request_properties(schema, "/api/v1/orgs/switch/", "application/json")


def test_bulk_delete_request_body_exposes_all_and_task_ids(schema: dict[str, Any]) -> None:
    """The authored bulk-delete request serializer surfaces ``all`` and ``task_ids``."""
    properties = _request_properties(schema, "/api/v1/sbom/jobs/artifacts/bulk-delete/", "application/json")

    assert "all" in properties
    assert "task_ids" in properties


def test_docs_endpoints_are_disabled_when_api_docs_disabled() -> None:
    """With API_DOCS_ENABLED=False the doc routes are not registered (404).

    Defined last: it reloads ``config.urls`` under an overridden setting, so keeping
    it at the end avoids disturbing the schema-generation tests above.
    """
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
