"""Smoke tests validating the backend scaffold imports and configures cleanly."""

from django.conf import settings

import generate_sbom


def test_package_exposes_version() -> None:
    """The backend package exposes a semantic version string."""
    assert generate_sbom.__version__ == "0.1.0"


def test_django_settings_load() -> None:
    """Django settings import and the core contrib apps are installed."""
    assert "django.contrib.auth" in settings.INSTALLED_APPS
    assert "django.contrib.staticfiles" in settings.INSTALLED_APPS
