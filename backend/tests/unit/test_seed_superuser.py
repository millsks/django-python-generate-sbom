"""Tests for the seed_superuser management command (Story 2.13)."""

import pytest
from django.core.management import call_command

from generate_sbom.users.models import User
from generate_sbom.users.services import get_the_admin_org, is_global_admin


@pytest.mark.django_db
def test_seed_superuser_creates_global_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the env vars set, the command creates the superuser as a global admin."""
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "root@example.com")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw12345678")

    call_command("seed_superuser")

    user = User.objects.get(email="root@example.com")
    assert user.is_superuser is True
    assert is_global_admin(user) is True
    assert get_the_admin_org() is not None


@pytest.mark.django_db
def test_seed_superuser_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running the command twice does not duplicate the user or error."""
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "root@example.com")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw12345678")

    call_command("seed_superuser")
    call_command("seed_superuser")

    assert User.objects.filter(email__iexact="root@example.com").count() == 1


@pytest.mark.django_db
def test_seed_superuser_skips_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the env vars unset, no user is created."""
    monkeypatch.delenv("DJANGO_SUPERUSER_EMAIL", raising=False)
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)

    call_command("seed_superuser")

    assert User.objects.filter(is_superuser=True).count() == 0
