"""Shared model abstractions for multi-tenant org isolation (AD-2).

Every model that owns org data extends :class:`OrgScopedModel`, which adds an
``org`` foreign key and the :class:`OrgScopedQuerySet` manager exposing
``.for_org(org)``. All queries against org-owned data must go through
``.for_org(org)`` so that org isolation is explicit and enforceable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from generate_sbom.users.models import Org


class OrgScopedQuerySet(models.QuerySet["OrgScopedModel"]):
    """QuerySet that constrains results to a single org."""

    def for_org(self, org: Org) -> OrgScopedQuerySet:
        """Return only the records owned by ``org``.

        Args:
            org: The organization to scope results to.

        Returns:
            A queryset filtered to rows whose ``org`` matches.
        """
        return self.filter(org=org)


OrgScopedManager = models.Manager.from_queryset(OrgScopedQuerySet)


class OrgScopedModel(models.Model):
    """Abstract base giving a model an ``org`` FK and org-scoped manager."""

    org = models.ForeignKey("users.Org", on_delete=models.CASCADE, related_name="+")

    objects = OrgScopedManager()

    class Meta:
        abstract = True
