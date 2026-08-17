"""Host-project views (Story 21.3).

Currently just the shell preview. Real pages live in the app
(``src/django_apps/inventory/``) and are added by Stories 21.5-21.18.
"""

from typing import Any

from django.views.generic import TemplateView


class ShellPreviewView(TemplateView):
    """Renders the project shell so the foundation is reviewable before any page exists.

    Mounted at ``/ui/`` because the SPA catch-all still owns the real page paths for the
    whole of Epic 21 (AC #7). Story 21.19 removes it along with the SPA.
    """

    template_name = "shell_preview.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the page title shown in the shell."""
        context = super().get_context_data(**kwargs)
        context["heading"] = "Server-rendered UI foundation"
        return context
