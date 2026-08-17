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

from inventory.users.pages import LoginPageView, LogoutPageView, RegisterPageView

urlpatterns = [
    path("login", LoginPageView.as_view(), name="ui-login"),
    path("register", RegisterPageView.as_view(), name="ui-register"),
    path("logout", LogoutPageView.as_view(), name="ui-logout"),
]
