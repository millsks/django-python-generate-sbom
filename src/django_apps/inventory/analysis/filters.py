"""django-filter filter sets for the analysis report tabs (Story 21.14 onward)."""

from __future__ import annotations

from typing import Any

from .tables import SEVERITY_RANK


def filter_by_severity(rows: list[dict[str, Any]], severity: str | None) -> list[dict[str, Any]]:
    """Narrow findings to one severity.

    A plain function rather than a ``FilterSet``: django-filter operates on querysets, and
    these rows come from a JSON artifact rather than the database. Keeping it explicit is
    clearer than forcing a queryset-shaped abstraction over a list.

    An unrecognised value yields **no rows** rather than silently showing everything, so a
    stale link cannot misrepresent a filtered view as complete.

    Args:
        rows: Flattened finding rows.
        severity: The requested severity, or None/"" for all.

    Returns:
        The matching rows.
    """
    if not severity:
        return rows
    if severity not in SEVERITY_RANK:
        return []
    return [row for row in rows if row["severity"] == severity]
