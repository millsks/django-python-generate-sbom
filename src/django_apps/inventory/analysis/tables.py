"""django-tables2 tables for the analysis report tabs (Story 21.14 onward)."""

from __future__ import annotations

from typing import Any

import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import SafeString

#: Severity ordering, carried over from VulnerabilitiesTab.tsx's SEVERITY_RANK. Severity must
#: sort by danger, not alphabetically — "Critical" before "High" before "Low" — so rows carry a
#: numeric rank and the column orders on that.
SEVERITY_RANK = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Unknown": 0}

#: The filter's options, most severe first.
SEVERITY_CHOICES = tuple((name, name) for name in SEVERITY_RANK)

#: Bootstrap contextual class per severity, replacing the SPA's coloured icons.
SEVERITY_BADGES = {
    "Critical": "text-bg-danger",
    "High": "text-bg-danger",
    "Medium": "text-bg-warning",
    "Low": "text-bg-secondary",
    "Unknown": "text-bg-light",
}


def vulnerability_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a vulnerability report into one row per finding.

    Mirrors ``toRows`` in the SPA: a package with three findings becomes three rows, and the
    identifier column merges the OSV id with its aliases, de-duplicated and order-preserving.

    Args:
        report: The stored report JSON.

    Returns:
        One dict per finding, each carrying a ``severity_rank`` for sorting.
    """
    rows: list[dict[str, Any]] = []
    for package in report.get("packages", []) or []:
        for finding in package.get("vulnerabilities", []) or []:
            identifiers = [finding.get("id"), *(finding.get("aliases") or [])]
            seen: dict[str, None] = {}
            for identifier in identifiers:
                if identifier:
                    seen.setdefault(identifier, None)
            severity = finding.get("severity") or "Unknown"
            rows.append(
                {
                    "name": package.get("name"),
                    "version": package.get("version"),
                    "ids": ", ".join(seen),
                    "cvss": finding.get("cvss_score"),
                    "severity": severity,
                    "severity_rank": SEVERITY_RANK.get(severity, 0),
                    "advisory_url": finding.get("advisory_url"),
                    "cwe": ", ".join(finding.get("cwe") or []),
                }
            )
    return rows


class VulnerabilityTable(tables.Table):
    """Vulnerable packages, one row per finding (converted from ``VulnerabilitiesTab.tsx``)."""

    name = tables.Column(verbose_name="Package")
    version = tables.Column(verbose_name="Version", default="—")
    ids = tables.Column(verbose_name="CVE / GHSA", default="—", orderable=False)
    cvss = tables.Column(verbose_name="CVSS", default="—")
    # Ordered by the numeric rank, never by the label — alphabetical severity would put
    # "Critical" after "High" and quietly bury the worst findings.
    severity = tables.Column(verbose_name="Severity", order_by="severity_rank")
    cwe = tables.Column(verbose_name="CWE", default="—", orderable=False)
    advisory_url = tables.Column(verbose_name="Advisory", orderable=False, default="")

    class Meta:
        # The SPA opened on severity descending, so the worst findings are first (Story 8.16).
        # This names the COLUMN, not the accessor: `severity` carries order_by="severity_rank",
        # so ordering by it sorts by danger. Naming the accessor here silently does nothing,
        # because tables2 resolves Meta.order_by against declared column names.
        order_by = "-severity"
        attrs = {"class": "table table-sm align-middle"}  # noqa: RUF012  # tables2 Meta option
        empty_text = "No findings match this filter."

    def render_severity(self, value: str) -> SafeString:
        """Render the severity as a badge, replacing the SPA's coloured icon."""
        return format_html('<span class="badge {}">{}</span>', SEVERITY_BADGES.get(value, "text-bg-light"), value)

    def render_advisory_url(self, value: str) -> SafeString:
        """Link out to the advisory (OSV, or the CVE's own page where one was found)."""
        if not value:
            return format_html("—")
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">Advisory</a>', value)
