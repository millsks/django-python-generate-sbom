"""Host-project views.

The shell preview (Story 21.3) and the landing page (Story 21.18). Real business pages
live in the app (``src/django_apps/inventory/``).

The active-org switcher lived here until Story 22.16 removed it: the organization is now
chosen on the upload form, shown as a column on Job Status, and written into the SBOM as its
supplier, so there is no longer a mode for the whole UI to sit in.
"""

from typing import Any

from django.views.generic import TemplateView


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
