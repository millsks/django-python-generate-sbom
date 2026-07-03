"""Tests for the SPA catch-all routing and SpaView (AD-5)."""

from pathlib import Path

import pytest
from django.test import Client
from django.urls import resolve

from generate_sbom.common.views import SpaView


def test_catchall_resolves_deep_route_to_spa() -> None:
    """A non-API browser route resolves to the SPA view (React Router mode)."""
    match = resolve("/dashboard")
    assert match.func.view_class is SpaView  # type: ignore[attr-defined]


def test_admin_is_not_shadowed_by_catchall() -> None:
    """The admin site is not swallowed by the SPA catch-all."""
    assert resolve("/admin/").app_name == "admin"


def test_spa_view_serves_index_when_built(tmp_path: Path, settings: pytest.FixtureRequest) -> None:
    """When the SPA is built, any non-API route returns index.html."""
    index = tmp_path / "index.html"
    index.write_text("<!doctype html><title>SPA OK</title>", encoding="utf-8")
    settings.SPA_INDEX_FILE = str(index)  # type: ignore[attr-defined]

    response = Client().get("/somewhere")

    assert response.status_code == 200
    assert b"SPA OK" in response.content


def test_spa_view_404_when_not_built(settings: pytest.FixtureRequest) -> None:
    """When the SPA is not built, the view returns 404 with a build hint."""
    settings.SPA_INDEX_FILE = "/nonexistent/index.html"  # type: ignore[attr-defined]

    response = Client().get("/whatever")

    assert response.status_code == 404
