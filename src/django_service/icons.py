"""Semantic icon names → sprite symbols (Story 21.18).

Story 12.2 centralised the SPA's icons in ``icons.ts`` precisely so a wholesale swap would be
a single-file change. This is the server-side equivalent: templates ask for ``nav.home`` or
``tab.vulnerabilities``, never for ``bi-house-door``, so replacing the icon set means editing
this mapping rather than hunting ``bi-*`` literals through twenty templates.

The values are symbol ids in ``static/images/icons.svg``. A name missing from the sprite is a
mistake worth failing loudly on, so :func:`symbol_for` raises rather than rendering an empty
box (see the template tag).
"""

from __future__ import annotations

#: Side-navigation destinations, matching `NavIcon` in icons.ts.
NAV = {
    "home": "house-door",
    "upload": "cloud-arrow-up",
    "history": "clock-history",
    "members": "people",
    "keys": "key",
    "organization": "building",
    "global_admins": "shield-lock",
}

#: Results tabs, matching `TabIcon` in icons.ts.
TAB = {
    "sbom": "file-earmark-code",
    "vulnerabilities": "shield-exclamation",
    "licenses": "file-earmark-text",
    "versions": "arrow-repeat",
}

#: Action affordances, matching the `*ActionIcon` exports in icons.ts.
ACTION = {
    "upload": "cloud-arrow-up",
    "export": "table",
    "download": "download",
    "add": "plus-lg",
    "delete": "trash",
    "logout": "box-arrow-right",
}

#: Application chrome that is not a nav destination or an action.
CHROME = {
    "brand": "box-seam",
    "menu": "list",
    "account": "person-circle",
    "theme_light": "sun",
    "theme_dark": "moon-stars",
    "repo": "github",
    "docs": "book",
    "api": "braces",
    "close": "x-lg",
}

_GROUPS = {"nav": NAV, "tab": TAB, "action": ACTION, "chrome": CHROME}


def symbol_for(name: str) -> str:
    """Resolve a semantic icon name like ``nav.home`` to its sprite symbol id.

    Args:
        name: ``<group>.<key>``, where group is nav, tab, action, or chrome.

    Returns:
        The sprite symbol id, without the ``#``.

    Raises:
        KeyError: If the group or key is unknown. Failing loudly beats rendering an invisible
            empty box, which is what a missing ``<use href="#...">`` silently produces.
    """
    group, _, key = name.partition(".")
    try:
        return _GROUPS[group][key]
    except KeyError as exc:
        raise KeyError(f"unknown icon {name!r}; add it to django_service/icons.py") from exc
