"""Server-rendered authentication pages (Story 21.5).

A separate module from ``views.py`` on purpose: the file-role convention that Story 21.2
preserved reserves ``views.py`` for **DRF** views. These are Django views rendering HTML,
and they call the same services the DRF views call — directly, never over HTTP (AD-1).

The DRF endpoints under ``/api/v1/auth/`` are untouched and still serve the SPA and any
API-key consumer.
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.http.response import HttpResponseBase
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView

from inventory.common.access import OrgContextMixin
from inventory.common.users import UserT
from inventory.users.auth import set_active_org_by_slug
from inventory.users.forms import (
    CreateApiKeyForm,
    CreateOrgForm,
)
from inventory.users.models import Org
from inventory.users.selectors import get_api_keys
from inventory.users.services import (
    MembershipError,
    create_api_key,
    create_org,
    revoke_api_key,
)

#: Where login sends a user who arrived without a `next` (the SPA's DEFAULT_AFTER_LOGIN).
DEFAULT_AFTER_LOGIN = "/"

#: Query/POST parameter carrying the originally requested page. Matches the name Django's
#: own `redirect_to_login` uses, which is what the Story 21.4 mixins emit.
REDIRECT_FIELD_NAME = "next"


class OrganizationHubView(OrgContextMixin, TemplateView):
    """The admin-facing hub (Story 2.11), converted from ``OrganizationPage.tsx``.

    It **links** to the management pages rather than duplicating their logic — the SPA page's
    own header comment made that explicit, and it is what keeps this page from drifting out of
    step with the pages it points at.
    """

    template_name = "inventory/orgs/hub.html"


class CreateOrgView(FormView):  # type: ignore[type-arg]
    """Create an organisation. Ungated since Story 21.24 (was global-admins-only, Story 2.12)."""

    template_name = "inventory/orgs/create.html"
    form_class = CreateOrgForm

    def form_valid(self, form: CreateOrgForm) -> HttpResponse:
        """Create the org — with the caller as its admin when there is one — then switch to it.

        An anonymous caller is the ordinary case after Story 21.24 and has no user to make an
        admin. Passing ``AnonymousUser`` straight through raised a ``ValueError`` from the
        membership FK, so this page returned **500** for the normal case until Story 22.8.
        """
        creator = cast(UserT, self.request.user) if self.request.user.is_authenticated else None
        org = create_org(name=form.cleaned_data["name"], admin_user=creator)
        # Make the new org the active one, so the admin lands in the thing they just made
        # rather than in whichever org happened to be active.
        set_active_org_by_slug(self.request, org.slug)
        messages.success(self.request, f"Created {org.name}.")
        return HttpResponseRedirect(reverse("ui-organization"))


KEYS_TEMPLATE = "inventory/keys/list.html"

#: Shown for a revoke that matches nothing. Deliberately identical whether the key never
#: existed or belongs to another org (AC #4, AD-2) — a distinction would confirm existence.
KEY_NOT_FOUND = "API key not found."


def _keys_context(request: HttpRequest, org: Org, form: CreateApiKeyForm | None = None) -> dict[str, Any]:
    """Build the keys-page context, defaulting to a blank create form."""
    return {
        "keys": get_api_keys(org),
        "org": org,
        "create_form": form or CreateApiKeyForm(),
    }


class ApiKeysView(OrgContextMixin, TemplateView):
    """List the active org's API keys.

    Gated on **membership**, not admin: ``KeysPage.tsx`` says so explicitly — "API Keys is
    viewable by any member; admin flag (create/revoke) comes from useAuth" — and the DRF
    ``KeysView.get`` matches. Only the create and revoke actions are admin-only.
    """

    template_name = KEYS_TEMPLATE

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Provide the org's active keys and a blank create form."""
        context = super().get_context_data(**kwargs)
        context.update(_keys_context(self.request, self.org))
        return context


class ApiKeyCreateView(OrgContextMixin, View):
    """Create a key and reveal the plaintext exactly once (AC #2, NFR-3.3)."""

    def post(self, request: HttpRequest) -> HttpResponseBase:
        """Create the key, rendering the plaintext on this response and nowhere else."""
        form = CreateApiKeyForm(request.POST)
        if form.is_valid():
            try:
                api_key, plaintext = create_api_key(self.org, name=form.cleaned_data["name"])
            except MembershipError as exc:
                # The 10-active-key limit (FR-2.2) arrives here as ApiKeyLimitError.
                form.add_error("name", exc.message)
            else:
                # RENDERED, never redirected. Only a HASH is stored (AD-8), so a key not
                # captured now is permanently unrecoverable — and stashing the plaintext in
                # the session to survive a redirect would put a live credential in the
                # session store. The story calls this a correctness constraint, not polish.
                return render(
                    request,
                    "inventory/keys/key_created.html",
                    {"api_key": api_key, "plaintext": plaintext, "org": self.org},
                )
        return render(request, KEYS_TEMPLATE, _keys_context(request, self.org, form))


class ApiKeyRevokeView(OrgContextMixin, View):
    """Soft-revoke a key belonging to the active org (FR-2.3)."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Revoke, reporting the same message whether the key is absent or another org's."""
        key_id = request.POST.get("key_id", "")
        # revoke_api_key scopes the lookup to `org`, so a key belonging to a different org
        # simply does not match — the wrong-org and never-existed cases are the same code
        # path and produce the same message (AC #4).
        if revoke_api_key(self.org, key_id):
            messages.success(request, "API key revoked.")
        else:
            messages.error(request, KEY_NOT_FOUND)
        return HttpResponseRedirect(reverse("ui-keys"))


# --- Platform administration (Story 21.8) -------------------------------------------------


#: Used when a revoke targets someone who is not on the tier. Identical whether the user does
