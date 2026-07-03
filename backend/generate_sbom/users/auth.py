"""Active-org resolution for a request — the single source of truth (AD-2).

Web UI requests carry the active org in the session; the Api-Key path (Story 2.4)
will carry it on ``request.auth.org``. Views resolve the acting org only through
``get_request_org`` so the "org is the first positional arg to every service"
rule holds uniformly regardless of auth mechanism.
"""

from __future__ import annotations

from typing import cast

from rest_framework.request import Request

from .models import Org, OrgMembership, User

SESSION_ACTIVE_ORG = "active_org_id"


def get_request_org(request: Request) -> Org | None:
    """Return the org this request is acting as, or None.

    Prefers the session's active org (validated against membership); falls back
    to the user's first membership and pins it in the session.
    """
    if not request.user.is_authenticated:
        return None
    user = request.user

    memberships = OrgMembership.objects.filter(user=user).select_related("org")
    active_id = request.session.get(SESSION_ACTIVE_ORG)
    if active_id is not None:
        membership = memberships.filter(org_id=active_id).first()
        if membership is not None:
            return membership.org

    membership = memberships.first()
    if membership is None:
        return None
    request.session[SESSION_ACTIVE_ORG] = membership.org_id
    return membership.org


def set_active_org_by_slug(request: Request, slug: str) -> Org | None:
    """Set the active org by slug if the user is a member; else return None."""
    user = cast(User, request.user)
    membership = OrgMembership.objects.filter(user=user, org__slug=slug).select_related("org").first()
    if membership is None:
        return None
    request.session[SESSION_ACTIVE_ORG] = membership.org_id
    return membership.org
