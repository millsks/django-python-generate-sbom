"""Tests for the /health/ endpoint (Story 1.2)."""

from django.test import Client


def test_health_returns_ok_without_auth() -> None:
    """GET /health/ returns 200 with {"status": "ok"} and requires no auth."""
    response = Client().get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
