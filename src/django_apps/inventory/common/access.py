"""Org context for the server-rendered pages, and the org-scoped lookup helper.

**This module no longer performs access control.** Story 21.24 removed the app's own
authentication outright: every page and every endpoint is reachable without logging in, and
identity becomes the *host platform's* responsibility, supplied via OIDC and group claims
when `inventory` is contributed to it (Epics 17-18). The three mixins that lived here —
``OrgMemberRequiredMixin``, ``OrgAdminRequiredMixin``, ``GlobalAdminRequiredMixin`` — and the
shared zero-org state they rendered are deleted, not disabled. ``git log`` has the diff if
the enforcement is ever wanted back, but it would be the wrong shape for the destination:
it was built on a Django session plus local ``OrgMembership`` roles.

**Tenancy is not authentication, and it survives untouched.** AD-2 makes the org the
isolation boundary regardless of who is asking, so:

* :class:`OrgContextMixin` resolves the acting org for a view. It is *not* a gate — it
  rejects nobody — it exists so nineteen view classes do not each repeat the same two lines,
  and so they keep the ``self.org`` attribute the deleted mixin used to supply.
* :func:`get_org_scoped_object_or_404` still refuses to serve another org's object, and
  still makes that refusal indistinguishable from a missing one.

CSRF protection, the POST-only org switcher, and the open-redirect guard on ``next`` are all
unaffected. This story removed *who you are*, not *what a browser may be made to do*.
"""

from __future__ import annotations

from typing import Any

from django.http import Http404, HttpRequest
from django.http.response import HttpResponseBase
from django.shortcuts import render
from django.views import View

from inventory.users.auth import get_request_org
from inventory.users.models import Org

#: Rendered in place of an org-scoped page when the database contains no organisation at
#: all. Distinct from the zero-org state Story 21.4 rendered and Story 21.24 deleted: that
#: one meant "you are not a member of one yet", which no longer has a subject.
NO_ORGS_TEMPLATE = "_no_orgs.html"


class OrgContextMixin(View):
    """Resolve the acting org onto ``self.org`` before the view body runs.

    Replaces ``OrgMemberRequiredMixin`` as the supplier of ``self.org``, minus the gate. The
    org comes from ``inventory.users.auth.get_request_org`` — the single source of truth
    shared with the API path (AD-2). A second resolver that drifts from it is precisely the
    class of bug that rule exists to prevent.

    When the database contains **no** organisation at all — an operator deleted every one,
    since migration ``0003`` seeds one — there is nothing for an org-scoped page to act on.
    This short-circuits to a shared explanatory page at 200 rather than raising, which keeps
    ``self.org`` a plain ``Org`` for every view body. Nineteen view classes would otherwise
    each need a ``None`` branch for a state none of them can do anything about.
    """

    #: Set by :meth:`dispatch` before the view runs. Never ``None`` inside the view.
    org: Org

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Resolve the acting org, or render the no-organisations page in place of the view."""
        org = get_request_org(request)
        if org is None:
            return render(request, NO_ORGS_TEMPLATE)
        self.org = org
        return super().dispatch(request, *args, **kwargs)


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
