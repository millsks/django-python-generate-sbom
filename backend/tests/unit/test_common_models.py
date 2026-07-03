"""Tests for the OrgScopedModel / OrgScopedQuerySet multi-tenancy primitive (AD-2)."""

from django.db import models

from generate_sbom.common.models import OrgScopedManager, OrgScopedModel, OrgScopedQuerySet
from generate_sbom.users.models import Org


class _ScopedThing(OrgScopedModel):
    """Concrete OrgScopedModel subclass used only for exercising the manager."""

    name = models.CharField(max_length=50)

    class Meta:
        app_label = "users"


def test_for_org_filters_by_org_id() -> None:
    """`.for_org(org)` constrains the query to the given org's rows."""
    org = Org(pk=42)
    sql = str(_ScopedThing.objects.for_org(org).query)
    assert "org_id" in sql
    assert "42" in sql


def test_for_org_returns_org_scoped_queryset() -> None:
    """`.for_org()` returns an OrgScopedQuerySet and the manager exposes it."""
    assert isinstance(_ScopedThing.objects.for_org(Org(pk=1)), OrgScopedQuerySet)
    assert hasattr(OrgScopedManager, "for_org")
