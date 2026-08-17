"""Template context shared by every server-rendered page (Story 21.3).

Two jobs, both there to stop templates from repeating themselves:

1. **The product name**, in its two forms. Story 12.6 established for the SPA that the
   name is defined once and never written as a literal in markup; this carries that rule
   to the Django side. Templates use ``{{ product_name }}`` / ``{{ product_name_short }}``.
2. **The navigation role gates.** ``base.html`` renders seven nav items, three of them
   role-gated. Computing that per template — or per view — would scatter authorization
   presentation across the codebase, so it is resolved once here.

The role gates are **presentation only**. Hiding a nav link is not authorization; the
views enforce access themselves (Story 21.4 adds the mixins that do it). The org lookup
goes through ``inventory.users.auth.get_request_org``, the single source of truth for the
acting org (AD-2) — never a reimplementation of it.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest

from inventory.users.auth import get_admin_org, get_request_org
from inventory.users.selectors import get_user_orgs
from inventory.users.services import is_global_admin


def ui(request: HttpRequest) -> dict[str, Any]:
    """Return the product name and the navigation state for this request.

    Args:
        request: The current request.

    Returns:
        A mapping merged into every template context.
    """
    context: dict[str, Any] = {
        "product_name": settings.PRODUCT_NAME,
        "product_name_short": settings.PRODUCT_NAME_SHORT,
        "product_version": settings.PRODUCT_VERSION,
        "repo_url": settings.REPO_URL,
        "docs_url": settings.DOCS_URL,
        # Derived, so the repo URL is still written down only once.
        "license_url": f"{settings.REPO_URL}/blob/main/LICENSE",
        "api_docs_url": "/api/docs/" if settings.API_DOCS_ENABLED else None,
        "active_org": None,
        "is_org_admin": False,
        "is_global_admin": False,
        # The orgs the switcher may offer. Empty for anonymous users; the switcher hides
        # itself below two entries (Story 2.19).
        "switchable_orgs": (),
    }

    user = request.user
    if not user.is_authenticated:
        return context

    context["active_org"] = get_request_org(request)
    context["is_org_admin"] = get_admin_org(request) is not None
    context["is_global_admin"] = is_global_admin(user)
    # get_user_orgs excludes the system ADMIN org, so a global admin is not offered it as a
    # workspace (Story 2.18) — the switcher lists exactly what they may act as.
    context["switchable_orgs"] = list(get_user_orgs(user))
    return context
