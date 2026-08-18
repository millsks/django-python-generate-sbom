"""Template context shared by every server-rendered page (Story 21.3).

Two jobs, both there to stop templates from repeating themselves:

1. **The product name**, in its two forms. Story 12.6 established for the SPA that the
   name is defined once and never written as a literal in markup; this carries that rule
   to the Django side. Templates use ``{{ product_name }}`` / ``{{ product_name_short }}``.
2. **The acting org and the switcher's options.** Every page shows which org it is acting
   as, and the switcher needs the list; resolving that per view would scatter it.

Story 21.24 removed the app's own authentication, so the role flags are now constant
``True``. They are **kept rather than deleted** because they mark where an authorization
decision belongs: Epics 17-18 reintroduce that decision from host-supplied group claims,
and these are the names the templates already read. Deleting them would mean re-threading
them through every template to put authorization back.

The org lookup goes through ``inventory.users.auth.get_request_org``, the single source of
truth for the acting org (AD-2) — never a reimplementation of it.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject

from inventory.users.auth import get_admin_org, get_request_org
from inventory.users.selectors import get_switchable_orgs


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
        # Lazy on purpose. This processor runs for EVERY template render, including ones
        # with no navigation at all (the API docs pages). Story 21.24 removed the
        # `is_authenticated` early return that used to skip the queries, so evaluating
        # eagerly would put two or three queries on every request in the project.
        "active_org": SimpleLazyObject(lambda: get_request_org(request)),
        # Constant since Story 21.24 — see the module docstring. `get_admin_org` is called
        # rather than hardcoded so the seam stays a single function to change.
        "is_org_admin": SimpleLazyObject(lambda: get_admin_org(request) is not None),
        "is_global_admin": True,
        # get_switchable_orgs excludes the system ADMIN org, so it is never offered as a
        # workspace (Story 2.18). The switcher hides itself below two entries (Story 2.19).
        "switchable_orgs": SimpleLazyObject(lambda: list(get_switchable_orgs())),
    }
    return context
