// Report → Excel sheet specs (Stories 8.12–8.15). One builder per report so the
// per-tab export and the Overview combined workbook produce identical sheets.
import type { LicenseReport, VersionEntry, VulnerabilityReport } from './api/reports'
import type { SheetSpec } from './excelExport'
import { registryUrl } from './registryLinks'

const onLtsCell = (onLts: boolean | null): string => (onLts === null ? '' : onLts ? 'yes' : 'no')

// Mirrors the Version Currency tab's columns, including the conda-forge latest, and
// links the package name to its registry page (PyPI / prefix.dev) in the sheet.
export function versionCurrencySheet(packages: VersionEntry[]): SheetSpec {
  return {
    name: 'Version Currency',
    columns: [
      { key: 'name', header: 'Package' },
      { key: 'installed', header: 'Installed' },
      { key: 'latest', header: 'Latest (PyPI)' },
      { key: 'conda_latest', header: 'conda-forge Latest' },
      { key: 'currency', header: 'Status' },
      { key: 'lts', header: 'LTS' },
      { key: 'on_lts', header: 'On LTS' },
      { key: 'ecosystem', header: 'Source' },
    ],
    rows: packages.map((pkg) => {
      const url = registryUrl({ name: pkg.name, version: pkg.installed, ecosystem: pkg.ecosystem })
      return {
        name: url ? { text: pkg.name, hyperlink: url } : pkg.name,
        installed: pkg.installed,
        latest: pkg.latest ?? '',
        conda_latest: pkg.conda_latest ?? '',
        currency: pkg.currency,
        lts: pkg.lts ?? '',
        on_lts: onLtsCell(pkg.on_lts),
        ecosystem: pkg.ecosystem ?? '',
      }
    }),
  }
}

// One row per finding across the FULL report (all severities, unfiltered). Multi-id
// and multi-CWE cells are comma-joined to mirror how the Vulnerabilities table renders
// them (VulnerabilitiesTab.toRows dedupes id + aliases the same way).
export function vulnerabilitiesSheet(report: VulnerabilityReport): SheetSpec {
  return {
    name: 'Vulnerabilities',
    columns: [
      { key: 'name', header: 'Package' },
      { key: 'version', header: 'Installed' },
      { key: 'ids', header: 'CVE / GHSA' },
      { key: 'cvss', header: 'CVSS' },
      { key: 'severity', header: 'Severity' },
      { key: 'cwe', header: 'CWE' },
      { key: 'advisory', header: 'Advisory URL' },
    ],
    rows: report.packages.flatMap((pkg) =>
      pkg.vulnerabilities.map((v) => ({
        name: pkg.name,
        version: pkg.version,
        ids: [...new Set([v.id, ...v.aliases])].join(', '),
        cvss: v.cvss_score ?? '',
        severity: v.severity,
        cwe: v.cwe.join(', '),
        advisory: v.advisory_url,
      })),
    ),
  }
}

// One row per package across every legal-risk tier (the FULL report). The tier name
// is carried alongside the license so a flat spreadsheet keeps the risk grouping.
export function licensesSheet(report: LicenseReport): SheetSpec {
  return {
    name: 'Licenses',
    columns: [
      { key: 'name', header: 'Package' },
      { key: 'version', header: 'Installed' },
      { key: 'license', header: 'License' },
      { key: 'tier', header: 'Risk Tier' },
    ],
    rows: report.tiers.flatMap((tier) =>
      tier.packages.map((pkg) => ({
        name: pkg.name,
        version: pkg.version,
        license: pkg.license,
        tier: tier.tier,
      })),
    ),
  }
}
