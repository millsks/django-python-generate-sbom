"""Host-project views.

The shell preview (Story 21.3) and the landing page (Story 21.18). Real business pages
live in the app (``src/django_apps/inventory/``).

The active-org switcher lived here until Story 22.16 removed it: the organization is now
chosen on the upload form, shown as a column on Job Status, and written into the SBOM as its
supplier, so there is no longer a mode for the whole UI to sit in.
"""

from typing import Any

from django.conf import settings
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


def _heading_lines(name: str) -> list[str]:
    """Split the product name for the landing heading, breaking after the ampersand.

    Done here rather than by putting a ``<br>`` in the setting, because that one string is also
    the ``<title>`` and the footer, where markup would be escaped and shown literally. Done here
    rather than left to the browser, because the natural wrap point moves with the viewport and
    the name reads as two halves — the framework, and what it inventories.

    A name without an ampersand yields a single line, so this cannot break a future rename.
    """
    head, separator, tail = name.partition("&")
    if not separator or not tail.strip():
        return [name]
    return [f"{head.strip()} {separator}", tail.strip()]


class LandingPageView(TemplateView):
    """The public landing page at ``/`` (Story 12.8 → 21.18).

    Deliberately **not** login-gated: an anonymous visitor is the audience, and the story is
    that they should understand the product before signing in.
    """

    template_name = "landing.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Supply the feature cards, steps, and the heading split across two lines."""
        context = super().get_context_data(**kwargs)
        context["product_name_lines"] = _heading_lines(settings.PRODUCT_NAME)
        context["features"] = LANDING_FEATURES
        context["steps"] = LANDING_STEPS
        return context
