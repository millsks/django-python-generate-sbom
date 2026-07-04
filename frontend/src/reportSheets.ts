// Report → Excel sheet specs (Stories 8.12–8.15). One builder per report so the
// per-tab export and the Overview combined workbook produce identical sheets.
import type { VersionEntry } from './api/reports'
import type { SheetSpec } from './excelExport'

const onLtsCell = (onLts: boolean | null): string => (onLts === null ? '' : onLts ? 'yes' : 'no')

export function versionCurrencySheet(packages: VersionEntry[]): SheetSpec {
  return {
    name: 'Version Currency',
    columns: [
      { key: 'name', header: 'Package' },
      { key: 'installed', header: 'Installed' },
      { key: 'latest', header: 'Latest' },
      { key: 'currency', header: 'Status' },
      { key: 'lts', header: 'LTS' },
      { key: 'on_lts', header: 'On LTS' },
      { key: 'ecosystem', header: 'Source' },
    ],
    rows: packages.map((pkg) => ({
      name: pkg.name,
      installed: pkg.installed,
      latest: pkg.latest ?? '',
      currency: pkg.currency,
      lts: pkg.lts ?? '',
      on_lts: onLtsCell(pkg.on_lts),
      ecosystem: pkg.ecosystem ?? '',
    })),
  }
}
