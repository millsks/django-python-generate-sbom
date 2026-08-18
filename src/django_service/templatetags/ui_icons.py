"""Template tag for rendering a sprite icon by semantic name (Story 21.18)."""

from __future__ import annotations

from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import SafeString

from django_service.icons import symbol_for

register = template.Library()


@register.simple_tag
def icon(name: str, size: int = 16, css_class: str = "bi") -> SafeString:
    """Render an icon by semantic name, e.g. ``{% icon 'tab.licenses' %}``.

    Args:
        name: ``<group>.<key>`` — see ``django_service.icons``.
        size: Pixel width and height.
        css_class: Classes for the ``<svg>``; ``bi`` gives it ``fill: currentColor``.

    Returns:
        The inline ``<svg><use>`` markup.
    """
    # aria-hidden throughout: every icon here sits beside its own visible label or inside a
    # control that carries an aria-label, so announcing it would only duplicate.
    return format_html(
        '<svg class="{}" width="{}" height="{}" aria-hidden="true"><use href="{}#bi-{}"/></svg>',
        css_class,
        size,
        size,
        static("images/icons.svg"),
        symbol_for(name),
    )
