"""django-tables2 tables for the analysis report tabs (Story 21.14 onward)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

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

    def render_advisory_url(self, value: str) -> str | SafeString:
        """Link out to the advisory (OSV, or the CVE's own page where one was found)."""
        if not value:
            # Plain text, not format_html("—"): format_html requires an argument and raises
            # TypeError on a bare literal — a crash that only fires for a finding with no
            # advisory URL, which no fixture had until Story 21.16 hit the same shape.
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">Advisory</a>', value)


#: Descending outdatedness, carried over from VersionsTab.tsx's CURRENCY_RANK. The order that
#: matters is behind-2+ > behind-1 > current > unknown; sorting the raw string instead would
#: give "behind-1, behind-2+, current, unknown", which looks sorted and is wrong.
CURRENCY_RANK = {"behind-2+": 3, "behind-1": 2, "current": 1, "unknown": 0}

#: Status label and Bootstrap class per currency class.
CURRENCY_BADGES = {
    "current": ("Current", "text-bg-success"),
    "behind-1": ("Behind 1", "text-bg-warning"),
    "behind-2+": ("Behind 2+", "text-bg-warning"),
    "unknown": ("Unknown", "text-bg-secondary"),
}

#: Human label per ecosystem; anything else has no known registry (registryLinks.ts).
ECOSYSTEM_LABELS = {"pypi": "PyPI", "conda": "Conda"}


def registry_url(name: str, version: str | None, ecosystem: str | None) -> str | None:
    """Return a package's registry detail page, or None when the ecosystem is unknown.

    Ported from ``registryLinks.ts`` (Story 8.9). Returning None rather than a guessed URL is
    deliberate: the caller renders plain text, which is better than a link that 404s.
    """
    quoted = quote(name, safe="")
    if ecosystem == "conda":
        return f"https://prefix.dev/channels/conda-forge/packages/{quoted}"
    if ecosystem == "pypi":
        return (
            f"https://pypi.org/project/{quoted}/{quote(version, safe='')}/"
            if version
            else f"https://pypi.org/project/{quoted}/"
        )
    return None


def version_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a version-currency report into table rows, adding the sort rank.

    Args:
        report: The stored report JSON.

    Returns:
        One dict per package, each carrying ``currency_rank`` for rank-aware ordering.
    """
    rows: list[dict[str, Any]] = []
    for package in report.get("packages", []) or []:
        currency = package.get("currency") or "unknown"
        rows.append(
            {
                **package,
                "currency": currency,
                "currency_rank": CURRENCY_RANK.get(currency, 0),
                "registry_url": registry_url(
                    package.get("name") or "", package.get("installed"), package.get("ecosystem")
                ),
            }
        )
    return rows


class VersionTable(tables.Table):
    """Version currency (converted from ``VersionsTab.tsx``).

    Column order is load-bearing: **PyPI Latest sits immediately before conda-forge Latest**
    so the two can be compared at a glance (Story 8.23). The SPA achieved that by ordering
    PyPI Latest last among its sortable columns and appending the rest; here the sequence is
    simply declared.
    """

    name = tables.Column(verbose_name="Package")
    installed = tables.Column(verbose_name="Installed", default="—")
    # Ordered by the numeric rank via the COLUMN name (see Meta.order_by below) — ordering on
    # the currency string itself is the defect this tab is most prone to.
    currency = tables.Column(verbose_name="Status", order_by="currency_rank")
    latest = tables.Column(verbose_name="PyPI Latest", default="—")
    conda_latest = tables.Column(verbose_name="conda-forge Latest", default="—", orderable=False)
    lts = tables.Column(verbose_name="LTS", default="—", orderable=False, empty_values=())
    ecosystem = tables.Column(verbose_name="Source", default="—", orderable=False)

    class Meta:
        # Story 8.16: package name ascending, matching VersionsTab.tsx's default.
        order_by = "name"
        attrs = {"class": "table table-sm align-middle"}  # noqa: RUF012  # tables2 Meta option
        empty_text = "No packages in this report."

    def render_name(self, value: str, record: dict[str, Any]) -> SafeString:
        """Link the package to its registry, or render plain text (Story 8.9)."""
        url = record.get("registry_url")
        if not url:
            return format_html("{}", value)
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, value)

    def render_currency(self, value: str) -> SafeString:
        """Render the currency class as a badge."""
        label, css = CURRENCY_BADGES.get(value, (value, "text-bg-secondary"))
        return format_html('<span class="badge {}">{}</span>', css, label)

    def render_conda_latest(self, value: str, record: dict[str, Any]) -> SafeString:
        """Flag a conda-forge latest that diverges from the PyPI latest (Story 8.10)."""
        if record.get("latest_mismatch"):
            return format_html('<span class="text-danger" title="Differs from the PyPI latest">{}</span>', value)
        return format_html("{}", value)

    def render_lts(self, record: dict[str, Any]) -> str | SafeString:
        """Show the tracked LTS series and whether the installed version is on it (Story 8.7).

        Three distinct states, as the SPA had them: no LTS tracked, on it, or targeting it.
        """
        lts = record.get("lts")
        if not lts:
            return "—"
        if record.get("on_lts"):
            return format_html('<span class="badge text-bg-success">On LTS ({})</span>', lts)
        return format_html('<span class="badge text-bg-info">LTS {} (target)</span>', lts)

    def render_ecosystem(self, value: str) -> str:
        """Show the human ecosystem label, or a dash when it is unknown."""
        return ECOSYSTEM_LABELS.get(value, "—")
