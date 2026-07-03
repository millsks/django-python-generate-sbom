"""Tests for the minimal Org model (Story 1.3)."""

import pytest

from generate_sbom.users.models import Org


@pytest.mark.django_db
def test_org_str_returns_name() -> None:
    """Org's string representation is its display name."""
    org = Org.objects.create(name="Acme", slug="acme")
    assert str(org) == "Acme"
