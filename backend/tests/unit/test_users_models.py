"""Tests for the users app models (Story 2.1)."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from generate_sbom.users.models import Org, OrgMembership, User


@pytest.mark.django_db
def test_org_str_returns_name() -> None:
    """Org's string representation is its display name."""
    org = Org.objects.create(name="Acme", slug="acme")
    assert str(org) == "Acme"


@pytest.mark.django_db
def test_user_is_email_based() -> None:
    """Users are created and identified by email, not username."""
    user = User.objects.create_user(email="alice@example.com", password="pw12345678")
    assert user.email == "alice@example.com"
    assert str(user) == "alice@example.com"
    assert User.USERNAME_FIELD == "email"


@pytest.mark.django_db
def test_create_superuser_sets_flags() -> None:
    """Superuser creation sets is_staff and is_superuser."""
    admin = User.objects.create_superuser(email="root@example.com", password="pw12345678")
    assert admin.is_staff
    assert admin.is_superuser


@pytest.mark.django_db
def test_membership_role_choices_enforced() -> None:
    """A role outside {admin, member} fails model validation (AC #3)."""
    user = User.objects.create_user(email="a@example.com", password="pw12345678")
    org = Org.objects.create(name="A", slug="a")
    membership = OrgMembership(org=org, user=user, role="bogus")
    with pytest.raises(ValidationError):
        membership.full_clean()


@pytest.mark.django_db
def test_membership_unique_per_org_user() -> None:
    """A user has at most one membership per org (unique_together)."""
    user = User.objects.create_user(email="a@example.com", password="pw12345678")
    org = Org.objects.create(name="A", slug="a")
    OrgMembership.objects.create(org=org, user=user, role=OrgMembership.Role.MEMBER)
    with pytest.raises(IntegrityError):
        OrgMembership.objects.create(org=org, user=user, role=OrgMembership.Role.ADMIN)
