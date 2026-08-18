"""Server-side Excel export (Story 21.17).

Replaces the browser-side exceljs export. This is the last piece that made Node a runtime
requirement, so Story 21.19 can remove the toolchain once this lands.

Ported faithfully from ``excelExport.ts`` and ``reportSheets.ts``: the same sheet names, the
same columns in the same order, the same row content, and the same two styled-cell kinds. The
column orders in particular are **not** to be tidied — Story 8.23 deliberately places PyPI
Latest immediately before conda-forge Latest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

from .tables import registry_url

#: MUI `error.main` (#D32F2F) as an ARGB, carried over from excelExport.ts so the divergence
#: warning is the same red in the sheet as on the page (Story 8.22).
RED_ARGB = "FFD32F2F"

#: The blue exceljs used for hyperlink text.
LINK_ARGB = "FF0563C1"

#: Excel forbids these in a sheet name, and caps it at 31 characters.
_ILLEGAL_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")
SHEET_NAME_LIMIT = 31


@dataclass(frozen=True)
class HyperlinkCell:
    """A clickable cell."""

    text: str
    hyperlink: str


@dataclass(frozen=True)
class RedTextCell:
    """A cell whose text carries a warning colour."""

    text: str


@dataclass
class SheetSpec:
    """One sheet: its name, its columns in order, and its rows."""

    name: str
    columns: list[tuple[str, str]]  # (key, header)
    rows: list[dict[str, Any]] = field(default_factory=list)


def safe_sheet_name(name: str) -> str:
    """Return an Excel-legal sheet name.

    Enforced here rather than trusted from the caller (AC #6): openpyxl raises on an illegal
    name, so a report title that happened to contain a slash would turn a download into a 500.
    """
    cleaned = _ILLEGAL_SHEET_CHARS.sub("-", name).strip() or "Sheet"
    return cleaned[:SHEET_NAME_LIMIT]


def build_workbook(sheets: list[SheetSpec]) -> bytes:
    """Render sheet specs to .xlsx bytes.

    Args:
        sheets: One spec per report. An empty list still yields a valid (empty) workbook.

    Returns:
        The serialised workbook.
    """
    workbook = Workbook()
    # openpyxl seeds a default sheet; remove it so sheet order and names are exactly the specs'.
    workbook.remove(workbook.active)

    for spec in sheets:
        worksheet = workbook.create_sheet(safe_sheet_name(spec.name))
        headers = [header for _key, header in spec.columns]
        worksheet.append(headers)
        for cell in worksheet[1]:
            cell.font = Font(bold=True)

        for row in spec.rows:
            worksheet.append([_plain_value(row.get(key)) for key, _header in spec.columns])
            written = worksheet[worksheet.max_row]
            for index, (key, _header) in enumerate(spec.columns):
                _apply_style(written[index], row.get(key))

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _plain_value(value: Any) -> Any:
    """Unwrap a styled cell to the value Excel stores."""
    if isinstance(value, HyperlinkCell | RedTextCell):
        return value.text
    return "" if value is None else value


def _apply_style(cell: Any, value: Any) -> None:
    """Apply hyperlink or red-font styling to a written cell."""
    if isinstance(value, HyperlinkCell):
        cell.hyperlink = value.hyperlink
        cell.font = Font(color=LINK_ARGB, underline="single")
    elif isinstance(value, RedTextCell):
        cell.font = Font(color=RED_ARGB)


# --- The four sheet builders, ported one-for-one from reportSheets.ts ----------------------


def _on_lts_cell(on_lts: bool | None) -> str:
    """Empty when unknown, else yes/no — matching ``onLtsCell``."""
    if on_lts is None:
        return ""
    return "yes" if on_lts else "no"


def version_currency_sheet(packages: list[dict[str, Any]]) -> SheetSpec:
    """Version currency, with the package name linked to its registry (Story 8.12)."""
    rows: list[dict[str, Any]] = []
    for package in packages:
        url = registry_url(package.get("name") or "", package.get("installed"), package.get("ecosystem"))
        name = package.get("name") or ""
        conda_latest = package.get("conda_latest")
        rows.append(
            {
                "name": HyperlinkCell(name, url) if url else name,
                "installed": package.get("installed") or "",
                "latest": package.get("latest") or "",
                # Red only when the conda-forge latest diverges AND a value is present —
                # the same two conditions the SPA required (Story 8.22).
                "conda_latest": (
                    RedTextCell(conda_latest)
                    if package.get("latest_mismatch") and conda_latest
                    else (conda_latest or "")
                ),
                "currency": package.get("currency") or "",
                "lts": package.get("lts") or "",
                "on_lts": _on_lts_cell(package.get("on_lts")),
                "ecosystem": package.get("ecosystem") or "",
            }
        )
    return SheetSpec(
        name="Version Currency",
        columns=[
            ("name", "Package"),
            ("installed", "Installed"),
            # Story 8.23: PyPI Latest immediately before conda-forge Latest. Do not reorder.
            ("latest", "PyPI Latest"),
            ("conda_latest", "conda-forge Latest"),
            ("currency", "Status"),
            ("lts", "LTS"),
            ("on_lts", "On LTS"),
            ("ecosystem", "Source"),
        ],
        rows=rows,
    )


def vulnerabilities_sheet(report: dict[str, Any]) -> SheetSpec:
    """One row per finding across the FULL report — all severities, unfiltered (Story 8.13)."""
    rows: list[dict[str, Any]] = []
    for package in report.get("packages") or []:
        for finding in package.get("vulnerabilities") or []:
            identifiers: dict[str, None] = {}
            for identifier in [finding.get("id"), *(finding.get("aliases") or [])]:
                if identifier:
                    identifiers.setdefault(identifier, None)
            rows.append(
                {
                    "name": package.get("name") or "",
                    "version": package.get("version") or "",
                    "ids": ", ".join(identifiers),
                    "cvss": finding.get("cvss_score") if finding.get("cvss_score") is not None else "",
                    "severity": finding.get("severity") or "",
                    "cwe": ", ".join(finding.get("cwe") or []),
                    "advisory": finding.get("advisory_url") or "",
                }
            )
    return SheetSpec(
        name="Vulnerabilities",
        columns=[
            ("name", "Package"),
            ("version", "Installed"),
            ("ids", "CVE / GHSA"),
            ("cvss", "CVSS"),
            ("severity", "Severity"),
            ("cwe", "CWE"),
            ("advisory", "Advisory URL"),
        ],
        rows=rows,
    )


def sbom_components_sheet(components: list[dict[str, Any]]) -> SheetSpec:
    """SBOM components (Story 8.27).

    The Ecosystem and PURL columns appear **only** when some component carries them, so the
    sheet reflects whatever the Components table currently shows (Story 8.26).
    """
    has_ecosystem = any(component.get("ecosystem") is not None for component in components)
    has_purl = any(component.get("purl") is not None for component in components)

    columns = [
        ("name", "Name"),
        ("version", "Version"),
        ("type", "Type"),
        ("license", "License"),
        ("relationship", "Relationship"),
    ]
    if has_ecosystem:
        columns.append(("ecosystem", "Ecosystem"))
    if has_purl:
        columns.append(("purl", "PURL"))

    rows = []
    for component in components:
        row: dict[str, Any] = {
            "name": component.get("name") or "",
            "version": component.get("version") or "",
            "type": component.get("type") or "",
            "license": component.get("license") or "",
            "relationship": component.get("relationship") or "",
        }
        if has_ecosystem:
            row["ecosystem"] = component.get("ecosystem") or ""
        if has_purl:
            row["purl"] = component.get("purl") or ""
        rows.append(row)

    return SheetSpec(name="SBOM Components", columns=columns, rows=rows)


def licenses_sheet(report: dict[str, Any]) -> SheetSpec:
    """One row per package across every tier, carrying the tier name (Story 8.14)."""
    rows = [
        {
            "name": package.get("name") or "",
            "version": package.get("version") or "",
            "license": package.get("license") or "",
            "tier": tier.get("tier") or "",
        }
        for tier in report.get("tiers") or []
        for package in tier.get("packages") or []
    ]
    return SheetSpec(
        name="Licenses",
        columns=[
            ("name", "Package"),
            ("version", "Installed"),
            ("license", "License"),
            ("tier", "Risk Tier"),
        ],
        rows=rows,
    )
