"""Overview metrics for the results page (Story 21.12).

Every value here comes from the job's ``summary_stats`` and nothing else. That column exists
precisely so the Overview does not fetch four report artifacts to render four cards
(NFR-2.2); reaching for the reports would reintroduce the cost the design avoided.

A metric backed by a **failed** phase reads "Unavailable" rather than 0 (FR-6.7) — a zero
would be a claim ("no vulnerabilities") the system cannot make when the scan did not run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Rendered wherever a phase failed or never produced a summary.
UNAVAILABLE = "Unavailable"


@dataclass(frozen=True)
class Metric:
    """One Overview card."""

    title: str
    value: str
    #: Tab this card deep-links to, or None when it is not a link.
    tab: str | None = None
    #: True when the underlying phase failed, so the template can style it differently.
    unavailable: bool = False


def _count(source: dict[str, Any], key: str) -> int:
    value = source.get(key)
    return value if isinstance(value, int) else 0


def _report(stats: dict[str, Any], name: str) -> dict[str, Any] | None:
    """Return a report's summary, or None if it is missing or failed."""
    reports = stats.get("reports")
    if not isinstance(reports, dict):
        return None
    report = reports.get(name)
    if not isinstance(report, dict) or report.get("failed"):
        return None
    return report


def build_metrics(summary_stats: dict[str, Any]) -> list[Metric]:
    """Build the Overview cards from a job's ``summary_stats``.

    Mirrors ``OverviewTab.tsx``'s value functions, including their wording, so the page reads
    the same before and after the conversion.

    Args:
        summary_stats: The job's stored summary; may be empty or partially populated.

    Returns:
        The cards, in the SPA's order.
    """
    stats = summary_stats or {}

    metrics = [Metric(title="Total packages", value=str(_count(stats, "total_packages")))]

    vuln = _report(stats, "vuln")
    metrics.append(
        Metric(
            title="Vulnerabilities",
            value=f"{_count(vuln, 'vulnerable_package_count')} vulnerable" if vuln else UNAVAILABLE,
            tab="vulnerabilities",
            unavailable=vuln is None,
        )
    )

    license_report = _report(stats, "license")
    if license_report is None:
        license_value = UNAVAILABLE
    else:
        copyleft = _count(license_report, "Strong Copyleft") + _count(license_report, "Weak Copyleft")
        license_value = (
            f"{_count(license_report, 'Permissive')} permissive · "
            f"{copyleft} copyleft · "
            f"{_count(license_report, 'Unknown')} unknown"
        )
    metrics.append(Metric(title="Licenses", value=license_value, tab="licenses", unavailable=license_report is None))

    version = _report(stats, "version")
    if version is None:
        version_value = UNAVAILABLE
    else:
        behind = _count(version, "behind-1") + _count(version, "behind-2+")
        version_value = f"{_count(version, 'current')} current · {behind} behind · {_count(version, 'unknown')} unknown"
    metrics.append(Metric(title="Version currency", value=version_value, tab="versions", unavailable=version is None))

    return metrics
