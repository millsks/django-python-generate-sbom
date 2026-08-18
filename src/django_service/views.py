"""Host-project views.

The shell preview (Story 21.3) and the active-org switcher (Story 21.4). Real business
pages live in the app (``src/django_apps/inventory/``) and are added by Stories 21.5-21.18.
"""

from typing import Any

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


class OrgSwitchView(View):
    """Set the caller's active organisation (Story 21.4, AC #3).

    **POST-only, and still CSRF-protected.** Story 21.24 removed the login requirement, not
    CSRF: this mutates session state, so it must not be reachable by a GET that a link, a
    prefetcher, or an image tag could trigger. Removing *who you are* does not remove
    *what a browser may be made to do on your behalf*.

    Calls ``set_active_org_by_slug`` **directly** rather than posting to
    ``/api/v1/orgs/switch/`` — AD-1 forbids the app talking to itself over HTTP.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        """Switch the active org, then return to the page the user came from."""
        slug = request.POST.get("slug", "")
        # An unknown slug — or the system ADMIN org, which is not a workspace (Story 2.12)
        # — returns None and changes nothing. Failing silently is correct: a miss means a
        # hand-edited request, and it should not be told which orgs exist.
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


#: The landing page's feature cards, carried over from HomePage.tsx's FEATURES.
LANDING_FEATURES = (
    {
        "icon": "tab.sbom",
        "title": "SBOM document",
        "blurb": "A standards-based CycloneDX/SPDX bill of materials — view it in-app or download it.",
    },
    {
        "icon": "tab.vulnerabilities",
        "title": "Vulnerability report",
        "blurb": "Known CVEs across your dependencies, ranked by severity.",
    },
    {
        "icon": "tab.licenses",
        "title": "License compliance",
        "blurb": "Every dependency&rsquo;s license, surfaced for review.",
    },
    {
        "icon": "tab.versions",
        "title": "Version currency",
        "blurb": "How far behind each package is — latest on PyPI vs conda-forge.",
    },
    {
        "icon": "action.export",
        "title": "Excel export",
        "blurb": "Export any report to a formatted spreadsheet.",
    },
)

#: The "how it works" steps, carried over from HomePage.tsx's STEPS.
LANDING_STEPS = (
    {"title": "Upload a manifest", "blurb": "requirements.txt, pyproject.toml, or environment.yml."},
    {
        "title": "Resolve & analyze",
        "blurb": "Dependencies are resolved and checked for vulnerabilities, licenses, and version currency.",
    },
    {"title": "Review the reports", "blurb": "Explore the SBOM, vulnerabilities, licenses, and versions."},
    {"title": "Export & share", "blurb": "Download the SBOM or export any report to Excel."},
)


class LandingPageView(TemplateView):
    """The public landing page at ``/`` (Story 12.8 → 21.18).

    Deliberately **not** login-gated: an anonymous visitor is the audience, and the story is
    that they should understand the product before signing in.
    """

    template_name = "landing.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Supply the feature cards and steps."""
        context = super().get_context_data(**kwargs)
        context["features"] = LANDING_FEATURES
        context["steps"] = LANDING_STEPS
        return context
