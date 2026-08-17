"""Host-project views.

The shell preview (Story 21.3) and the active-org switcher (Story 21.4). Real business
pages live in the app (``src/django_apps/inventory/``) and are added by Stories 21.5-21.18.
"""

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from inventory.users.auth import set_active_org_by_slug


class ShellPreviewView(TemplateView):
    """Renders the project shell so the foundation is reviewable before any page exists.

    Mounted at ``/ui/`` because the SPA catch-all still owns the real page paths for the
    whole of Epic 21 (Story 21.3 AC #7). Story 21.19 removes it along with the SPA.
    """

    template_name = "shell_preview.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the page title shown in the shell."""
        context = super().get_context_data(**kwargs)
        context["heading"] = "Server-rendered UI foundation"
        return context


class OrgSwitchView(LoginRequiredMixin, View):
    """Set the caller's active organisation (Story 21.4, AC #3).

    POST-only on purpose: this mutates session state, so it must carry CSRF and must not be
    reachable by a GET (which a link, a prefetcher, or an image tag could trigger).

    Calls ``set_active_org_by_slug`` **directly** rather than posting to ``/api/v1/orgs/switch/``
    — AD-1 forbids the app talking to itself over HTTP, and the service already validates
    membership, so an unauthorised slug simply does not switch.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        """Switch the active org, then return to the page the user came from."""
        slug = request.POST.get("slug", "")
        # A slug the user is not a member of returns None and changes nothing. Failing
        # silently is correct here: the switcher only ever offers orgs the user belongs to,
        # so a miss means a tampered request, and it should not be told the org exists.
        set_active_org_by_slug(request, slug)
        return HttpResponseRedirect(self._safe_next(request))

    @staticmethod
    def _safe_next(request: HttpRequest) -> str:
        """Return the validated redirect target, defaulting to the home page.

        Validating against the current host is what stops the ``next`` parameter becoming
        an open redirect.
        """
        target = request.POST.get("next", "")
        if target and url_has_allowed_host_and_scheme(
            target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return target
        return "/"
