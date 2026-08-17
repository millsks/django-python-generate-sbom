"""Server-side access control for the server-rendered pages (Story 21.4).

Replaces four **client-side** React route guards (`ProtectedRoute`, `OrgRoute`,
`AdminRoute`, `GlobalAdminRoute`) with enforcement the browser cannot bypass. The SPA's
own guards described themselves as "UX, not the security boundary" — the API was the
boundary. Server-rendered pages have no such second line, so these mixins *are* the
boundary and are tested as such.

Three rules, and the reasoning behind each:

**Anonymous → redirect to login, preserving the destination.** They can fix the problem by
signing in, so send them somewhere useful. Django's ``AccessMixin.handle_no_permission``
already does exactly this (via ``redirect_to_login`` with ``next``), which is why these
mixins build on it rather than reimplementing the branch.

**Authenticated but wrong role → 403, never a redirect.** A redirect turns an authorization
failure into a navigation event, which hides it from tests and from logs. This is a
deliberate divergence from the SPA, whose guards bounced wrong-role users to the home page.

**Authenticated with no active org → the shared "no organisation" state, not an error.**
A user who has not been added to an org yet has done nothing wrong. Story 2.18 kept such
users off org-scoped pages; here the mixin renders the empty state in place of the page, so
every org-scoped page behaves identically without repeating itself (Story 21.4 AC #4, and
Task 4's "enforce at the mixin layer, not per page").

Org resolution goes through ``inventory.users.auth`` — the single source of truth shared
with the API path (AD-2). A second resolver that drifts from the API's is precisely the
class of bug this story exists to prevent.
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, HttpRequest
from django.http.response import HttpResponseBase
from django.shortcuts import render

from inventory.common.users import UserT
from inventory.users.auth import get_admin_org, get_request_org
from inventory.users.models import Org
from inventory.users.services import is_global_admin

#: Rendered in place of an org-scoped page when the user belongs to no organisation.
NO_ORG_TEMPLATE = "_no_org.html"


class OrgMemberRequiredMixin(LoginRequiredMixin):
    """Require an authenticated user with an active organisation.

    Replaces ``OrgRoute.tsx``. On success the resolved org is available to the view as
    ``self.org``, so pages never re-resolve it (and cannot resolve it differently).
    """

    #: Set by :meth:`dispatch` before the view runs. Never ``None`` inside the view.
    org: Org

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Resolve the active org, or short-circuit to login / the no-org state."""
        if not request.user.is_authenticated:
            # LoginRequiredMixin redirects to the login URL carrying `next`.
            return super().dispatch(request, *args, **kwargs)

        org = get_request_org(request)
        if org is None:
            # 200, not 403 or a redirect: nothing is forbidden and nothing is missing —
            # the account simply has no organisation yet. Returning the page's own URL
            # with this body means the URL is not a way to reach org data.
            return render(request, NO_ORG_TEMPLATE)

        self.org = org
        return super().dispatch(request, *args, **kwargs)


class OrgAdminRequiredMixin(OrgMemberRequiredMixin, AccessMixin):
    """Require an admin of the **active** organisation.

    Replaces ``AdminRoute.tsx``. Admin-ness is per-org, not global: the same user can be an
    admin of org A and a plain member of org B, so this is re-evaluated against whichever
    org is active. Switching org can therefore change the answer.
    """

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Reject non-admins of the active org with 403."""
        if request.user.is_authenticated and get_request_org(request) is not None and get_admin_org(request) is None:
            # Authenticated, has an org, but is not its admin → a real authorization
            # failure, so 403 rather than a redirect.
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class GlobalAdminRequiredMixin(UserPassesTestMixin):
    """Require a member of the distinguished ADMIN org — the platform-admin tier.

    Replaces ``GlobalAdminRoute.tsx``. Deliberately **not** built on
    :class:`OrgMemberRequiredMixin`: global-admin pages are platform-wide and must stay
    reachable by a global admin who has no working org of their own (Story 2.18 makes the
    ADMIN org never resolve as a working org, so such a user has no active org at all).

    ``UserPassesTestMixin.handle_no_permission`` supplies the required split for free:
    anonymous → redirect to login with ``next``; authenticated non-global-admin → 403.
    """

    #: Supplied by the ``View`` this mixin is combined with. Declared so the mixin type-checks
    #: on its own, and to document that it is only ever valid on a view.
    request: HttpRequest

    def test_func(self) -> bool:
        """Return True if the requesting user is a global admin."""
        user = self.request.user
        if not user.is_authenticated:
            return False
        # `is_authenticated` is a plain bool property, not a TypeGuard, so it does not narrow
        # the User | AnonymousUser union for mypy. The check above makes the cast sound.
        return is_global_admin(cast("UserT", user))


def get_org_scoped_object_or_404(model: Any, org: Org, **lookup: Any) -> Any:
    """Fetch one org-owned object, or raise ``Http404`` (AD-2).

    Wrong-org and non-existent must be **indistinguishable** to the caller — otherwise a
    404-vs-403 difference tells an attacker that an object they cannot see does exist. The
    SPA relied on the same rule (``useJobStatus.ts``: "Cross-org and unknown jobs both
    surface as 403/404 — no existence leak"), and the server-rendered path must preserve
    it. So the org filter is applied as part of the query rather than checked afterwards:
    there is no code path here that can distinguish the two cases, by construction.

    Args:
        model: An ``OrgScopedModel`` subclass.
        org: The organisation the caller is acting as.
        **lookup: Field lookups identifying the object within that org.

    Returns:
        The matching instance.

    Raises:
        Http404: If no object matches — whether because it does not exist or because it
            belongs to a different organisation.
    """
    instance = model.objects.for_org(org).filter(**lookup).first()
    if instance is None:
        raise Http404
    return instance
