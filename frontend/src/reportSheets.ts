// Report → Excel sheet specs (Stories 8.12–8.15). One builder per report so the
// per-tab export and the Overview combined workbook produce identical sheets.
import type { LicenseReport, VersionEntry, VulnerabilityReport } from './api/reports'
import type { SbomDocument } from './api/sbom'
import type { ExcelColumn, SheetSpec } from './excelExport'
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
      { key: 'latest', header: 'PyPI Latest' },
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
        // Carry the UI's divergence red into the sheet (Story 8.22): red only when the
        // conda-forge latest diverges from the PyPI latest and a value is present.
        conda_latest:
          pkg.latest_mismatch && pkg.conda_latest
            ? { text: pkg.conda_latest, redText: true }
            : (pkg.conda_latest ?? ''),
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

// Mirrors the SBOM tab's Components view (Story 8.27): one row per component with the
// same Name/Version/Type/License/Relationship columns. The Ecosystem and PURL columns
// are emitted only when the normalized components carry those fields (Story 8.26), so the
// sheet always reflects whatever the Components table currently shows.
export function sbomComponentsSheet(doc: SbomDocument): SheetSpec {
  const components = doc.components
  const hasEcosystem = components.some((c) => c.ecosystem != null)
  const hasPurl = components.some((c) => c.purl != null)
  const columns: ExcelColumn[] = [
    { key: 'name', header: 'Name' },
    { key: 'version', header: 'Version' },
    { key: 'type', header: 'Type' },
    { key: 'license', header: 'License' },
    { key: 'relationship', header: 'Relationship' },
  ]
  if (hasEcosystem) columns.push({ key: 'ecosystem', header: 'Ecosystem' })
  if (hasPurl) columns.push({ key: 'purl', header: 'PURL' })
  return {
    name: 'SBOM Components',
    columns,
    rows: components.map((c) => {
      const row: Record<string, unknown> = {
        name: c.name,
        version: c.version ?? '',
        type: c.type ?? '',
        license: c.license ?? '',
        relationship: c.relationship ?? '',
      }
      if (hasEcosystem) row.ecosystem = c.ecosystem ?? ''
      if (hasPurl) row.purl = c.purl ?? ''
      return row
    }),
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
