"""Read-only queries for the users app (AD-3: plain in/out)."""

from __future__ import annotations

from django.db.models import QuerySet

from .models import Org, OrgApiKey, OrgMembership, User


def get_user_orgs(user: User) -> QuerySet[Org]:
    """Return the non-ADMIN orgs the user belongs to, ordered by name.

    The system ADMIN org (``is_admin_org=True``, Story 2.8) is excluded — it is a
    meta org, not a switchable workspace (Story 2.12), so it never appears in the
    org switcher / ``OrgListView`` even for a global admin (a member of every org).
    """
    return Org.objects.filter(memberships__user=user, is_admin_org=False).order_by("name")


def get_org_members(org: Org) -> QuerySet[OrgMembership]:
    """Return the memberships of ``org`` (with users), ordered by email."""
    return OrgMembership.objects.filter(org=org).select_related("user").order_by("user__email")


def get_api_keys(org: Org) -> QuerySet[OrgApiKey]:
    """Return the active (non-revoked) API keys of ``org``, newest first."""
    return OrgApiKey.objects.filter(org=org, revoked_at__isnull=True).order_by("-created")
