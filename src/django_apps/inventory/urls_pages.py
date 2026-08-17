"""URLconf for the app's server-rendered pages (Story 21.5 onward).

Kept apart from the per-submodule ``urls.py`` files, which are the **DRF** urlconfs mounted
under ``/api/v1/``. This one is mounted at the site root by ``config/urls.py`` and is where
Stories 21.5-21.18 register each page as it is converted.

**Route names are prefixed ``ui-``.** The API urlconfs already own the obvious names
(``login``, ``register``, ``org-switch``, ``sbom-jobs``, …), and Django resolves a duplicate
``name=`` to whichever pattern is registered LAST — which is the API, since ``config/urls.py``
includes it after these. In Story 21.4 that silently pointed an HTML form at a JSON endpoint,
so the prefix is load-bearing, not cosmetic.

Every path added here must also be added to the SPA catch-all's negative lookahead in
``config/urls.py``, or the catch-all will shadow it.
"""

from django.urls import path

from inventory.users.pages import (
    ApiKeyCreateView,
    ApiKeyRevokeView,
    ApiKeysView,
    CreateOrgView,
    LeaveOrgView,
    LoginPageView,
    LogoutPageView,
    MemberAddExistingView,
    MemberCreateUserView,
    MemberDemoteView,
    MemberPromoteView,
    MemberRemoveView,
    MembersView,
    OrganizationHubView,
    RegisterPageView,
)

urlpatterns = [
    # Story 21.5 — authentication
    path("login", LoginPageView.as_view(), name="ui-login"),
    path("register", RegisterPageView.as_view(), name="ui-register"),
    path("logout", LogoutPageView.as_view(), name="ui-logout"),
    # Story 21.6 — organisation administration
    path("organization", OrganizationHubView.as_view(), name="ui-organization"),
    path("organization/create", CreateOrgView.as_view(), name="ui-org-create"),
    path("organization/leave", LeaveOrgView.as_view(), name="ui-org-leave"),
    # Story 21.6 — members. Each mutation gets its own POST endpoint rather than one view
    # switching on an `action` field, so the URL itself says what happened and each is
    # independently gated and testable.
    path("members", MembersView.as_view(), name="ui-members"),
    path("members/add", MemberAddExistingView.as_view(), name="ui-member-add"),
    path("members/create", MemberCreateUserView.as_view(), name="ui-member-create"),
    path("members/remove", MemberRemoveView.as_view(), name="ui-member-remove"),
    path("members/promote", MemberPromoteView.as_view(), name="ui-member-promote"),
    path("members/demote", MemberDemoteView.as_view(), name="ui-member-demote"),
    # Story 21.7 — API keys. Listing is member-level; create and revoke are admin-only,
    # matching the DRF endpoints exactly.
    path("keys", ApiKeysView.as_view(), name="ui-keys"),
    path("keys/create", ApiKeyCreateView.as_view(), name="ui-key-create"),
    path("keys/revoke", ApiKeyRevokeView.as_view(), name="ui-key-revoke"),
]
