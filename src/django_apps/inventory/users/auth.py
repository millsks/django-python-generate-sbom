"""Active-org resolution for a request — the single source of truth (AD-2).

Web UI requests carry the active org in the session; the Api-Key path (Story 2.4)
carries it on ``request.auth.org``. Views resolve the acting org only through
``get_request_org`` so the "org is the first positional arg to every service"
rule holds uniformly regardless of auth mechanism.

These accept a plain ``HttpRequest`` as well as a DRF ``Request`` (Story 21.3): the
server-rendered pages and the navigation context processor are not DRF views, and they
must resolve the acting org through this module rather than reimplementing it. Only DRF
requests carry ``.auth``, hence the ``getattr`` guard.
"""

from __future__ import annotations

from typing import cast

from django.http import HttpRequest
from rest_framework.request import Request

from inventory.common.users import UserT, user_ref

from .models import Org, OrgApiKey, OrgMembership

SESSION_ACTIVE_ORG = "active_org_id"


def get_request_org(request: HttpRequest | Request) -> Org | None:
    """Return the org this request is acting as, or None.

    Api-Key requests carry the org on ``request.auth.org``. Session requests use
    the session's active org (validated against membership), falling back to the
    user's first non-ADMIN membership and pinning it in the session.
    """
    api_key = getattr(request, "auth", None)
    if isinstance(api_key, OrgApiKey):
        return api_key.org

    if not request.user.is_authenticated:
        return None
    user = request.user

    memberships = OrgMembership.objects.filter(user=user_ref(user)).select_related("org")
    active_id = request.session.get(SESSION_ACTIVE_ORG)
    if active_id is not None:
        # Exclude the system ADMIN org even when it is pinned in the session (Story 2.18):
        # a global admin whose only membership is the ADMIN org must resolve to zero-org,
        # never have the ADMIN org act as their working org.
        membership = memberships.filter(org_id=active_id, org__is_admin_org=False).first()
        if membership is not None:
            return membership.org

    # Fall back to a real workspace, never the system ADMIN org (Story 2.12) — a
    # global admin is a member of every org, so an unfiltered first() could pin them
    # to the ADMIN org.
    membership = memberships.filter(org__is_admin_org=False).first()
    if membership is None:
        return None
    request.session[SESSION_ACTIVE_ORG] = membership.org_id
    return membership.org


def set_active_org_by_slug(request: HttpRequest | Request, slug: str) -> Org | None:
    """Set the active org by slug if the user is a member; else return None."""
    user = cast(UserT, request.user)
    membership = OrgMembership.objects.filter(user=user_ref(user), org__slug=slug).select_related("org").first()
    if membership is None:
        return None
    request.session[SESSION_ACTIVE_ORG] = membership.org_id
    return membership.org


def get_admin_org(request: HttpRequest | Request) -> Org | None:
    """Return the active org if the caller is an admin of it, else None (AD-2).

    Server-side authorization for admin-only membership actions; UI hiding is not
    a substitute for this check.
    """
    org = get_request_org(request)
    if org is None:
        return None
    user = cast(UserT, request.user)
    is_admin = OrgMembership.objects.filter(org=org, user=user_ref(user), role=OrgMembership.Role.ADMIN).exists()
    return org if is_admin else None
