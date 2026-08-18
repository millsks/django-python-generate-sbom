"""Read-only queries for the users app (AD-3: plain in/out)."""

from __future__ import annotations

from django.conf import settings
from django.db.models import QuerySet

from inventory.common.users import UserT

from .models import Org, OrgApiKey, OrgMembership


def get_default_org() -> Org | None:
    """Return the org an anonymous caller acts as, or None (Story 21.24).

    Prefers the org named by ``settings.INVENTORY_DEFAULT_ORG_SLUG`` (seeded by migration
    ``0003``), falling back to the first non-ADMIN org by name so a deployment that renamed
    or removed the seeded org still resolves somewhere sensible.

    Returns ``None`` only when no non-ADMIN org exists at all — an operator deleted every
    workspace. That renders empty pages rather than raising: a 500 on every route is a worse
    answer to a recoverable data state than an empty list, and creating an org on the fly
    from a GET would be a side effect no reader expects.

    **Never returns the ADMIN org.** It is a meta org rather than a workspace (Stories
    2.12/2.18); pointing the anonymous default at it would resurrect the bug those fixed.
    """
    pinned = Org.objects.filter(is_admin_org=False, slug=settings.INVENTORY_DEFAULT_ORG_SLUG).first()
    if pinned is not None:
        return pinned
    return Org.objects.filter(is_admin_org=False).order_by("name").first()


def get_switchable_orgs(user: UserT | None = None) -> QuerySet[Org]:
    """Return every non-ADMIN org, ordered by name (Story 21.24).

    Was ``get_user_orgs``, which filtered by membership. With authentication removed there
    is no membership to filter by, so the name would have lied — every org is switchable.
    The ``user`` argument is accepted and ignored so the two call sites did not each need a
    conditional; it is the seam an OIDC-supplied identity would use to narrow this again
    (Epics 17-18).

    The system ADMIN org (``is_admin_org=True``, Story 2.8) is still excluded — it is a
    meta org, not a switchable workspace (Story 2.12).
    """
    return Org.objects.filter(is_admin_org=False).order_by("name")


def get_org_members(org: Org) -> QuerySet[OrgMembership]:
    """Return the memberships of ``org`` (with users), ordered by email."""
    return OrgMembership.objects.filter(org=org).select_related("user").order_by("user__email")


def get_api_keys(org: Org) -> QuerySet[OrgApiKey]:
    """Return the active (non-revoked) API keys of ``org``, newest first."""
    return OrgApiKey.objects.filter(org=org, revoked_at__isnull=True).order_by("-created")
