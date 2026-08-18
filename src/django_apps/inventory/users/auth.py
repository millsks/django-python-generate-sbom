"""Active-org resolution for a request — the single source of truth (AD-2).

There are three paths, tried in this order. The Api-Key path (Story 2.4) carries the org on
``request.auth.org``. A session-authenticated user (Django's ``/admin/`` still has a login)
carries it in the session. **Everyone else is anonymous and acts as the default org**
(Story 21.24) — the app has no authentication of its own, and identity becomes the host
platform's responsibility when `inventory` is contributed to it (Epics 17-18).

Views resolve the acting org only through ``get_request_org`` so the "org is the first
positional arg to every service" rule holds uniformly regardless of how the caller arrived.
Never write a second resolver: a change here is a change to every page and endpoint at once,
which is the point.

These accept a plain ``HttpRequest`` as well as a DRF ``Request`` (Story 21.3): the
server-rendered pages and the navigation context processor are not DRF views, and they
must resolve the acting org through this module rather than reimplementing it. Only DRF
requests carry ``.auth``, hence the ``getattr`` guard.
"""

from __future__ import annotations

from django.http import HttpRequest
from rest_framework.request import Request

from inventory.common.users import user_ref

from .models import Org, OrgApiKey, OrgMembership
from .selectors import get_default_org

SESSION_ACTIVE_ORG = "active_org_id"


def get_request_org(request: HttpRequest | Request) -> Org | None:
    """Return the org this request is acting as, or None.

    Api-Key requests carry the org on ``request.auth.org``. Anonymous requests get the
    default org (Story 21.24). Session requests use the session's active org, falling back
    to the user's first non-ADMIN membership and pinning it in the session.

    Returns ``None`` only when no usable org exists at all — see ``get_default_org``.
    """
    api_key = getattr(request, "auth", None)
    if isinstance(api_key, OrgApiKey):
        return api_key.org

    if not request.user.is_authenticated:
        # Story 21.24: anonymous is the ordinary case now, not a rejected one. This is the
        # same shape the Api-Key path has always produced — AnonymousUser plus a resolved
        # org — which is why every downstream selector, template, and serializer already
        # copes, and why jobs created this way simply carry `user=None`.
        return get_default_org()
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
        # Story 21.24: a signed-in user with no membership falls back to the same default
        # org an anonymous caller gets. Returning None here would give a logged-in user a
        # WORSE experience than an anonymous one, and would make "no org" ambiguous between
        # "you are not a member of one" (no longer a concept) and "none exists" (the only
        # remaining meaning, which the no-organisations page states).
        return get_default_org()
    request.session[SESSION_ACTIVE_ORG] = membership.org_id
    return membership.org


def set_active_org_by_slug(request: HttpRequest | Request, slug: str) -> Org | None:
    """Set the active org by slug, or return None if no such switchable org exists.

    Story 21.24 removed the membership check: with no authentication there is no membership
    to check against, and every non-ADMIN org is switchable. The ADMIN org is still refused
    (Story 2.12) — it is a meta org, not a workspace, so it must not become the active one
    by way of a hand-typed slug.
    """
    org = Org.objects.filter(slug=slug, is_admin_org=False).first()
    if org is None:
        return None
    request.session[SESSION_ACTIVE_ORG] = org.pk
    return org


def get_admin_org(request: HttpRequest | Request) -> Org | None:
    """Return the org this request is acting as (Story 21.24).

    Was "the active org **if** the caller is an admin of it". With authentication removed
    there is no principal to be an admin, so admin capability is universal and this is now
    the same answer as :func:`get_request_org`.

    It is kept as a distinct function rather than inlined at its call sites because it marks
    *where an authorization decision belongs*. Epics 17-18 reintroduce that decision from
    host-supplied group claims, and this is the seam it goes back into.
    """
    return get_request_org(request)
