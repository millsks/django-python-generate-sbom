"""Read-only queries for the users app (AD-3: plain in/out)."""

from __future__ import annotations

from django.db.models import QuerySet

from .models import Org, OrgMembership, User


def get_user_orgs(user: User) -> QuerySet[Org]:
    """Return the orgs the given user belongs to, ordered by name."""
    return Org.objects.filter(memberships__user=user).order_by("name")


def get_org_members(org: Org) -> QuerySet[OrgMembership]:
    """Return the memberships of ``org`` (with users), ordered by email."""
    return OrgMembership.objects.filter(org=org).select_related("user").order_by("user__email")
