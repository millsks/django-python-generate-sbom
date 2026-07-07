// Overview tab (Story 5.2): at-a-glance summary cards sourced entirely from the
// job's summary_stats (no per-report fetch — NFR-2.2), a SBOM download, and
// deep-links into the detail tabs. A metric backed by a failed phase shows
// "Unavailable" rather than a misleading 0 (FR-6.7).
import { useState, type ReactNode } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardActionArea from '@mui/material/CardActionArea'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import type { JobStatus, ReportSummary } from '../api/jobs'
import { getLicenses, getVersions, getVulnerabilities } from '../api/reports'
import { getSbomDocument } from '../api/sbom'
import { buildWorkbook, downloadWorkbook, type SheetSpec } from '../excelExport'
import { DownloadActionIcon, ExportIcon } from '../icons'
import { licensesSheet, sbomComponentsSheet, versionCurrencySheet, vulnerabilitiesSheet } from '../reportSheets'

// Tab indices in the shell's fixed order (5.1; SBOM inserted at 1 in 8.6).
const TAB = { vulnerabilities: 2, licenses: 3, versions: 4 }

const num = (value: unknown): number => (typeof value === 'number' ? value : 0)

const reportAvailable = (report: ReportSummary | undefined): boolean => Boolean(report && !report.failed)

function MetricCard({ title, value, onClick }: { title: string; value: ReactNode; onClick?: () => void }) {
  const body = (
    <CardContent>
      <Typography variant="overline" color="text.secondary">
        {title}
      </Typography>
      <Typography variant="h6" component="div">
        {value}
      </Typography>
    </CardContent>
  )
  return (
    <Card variant="outlined" sx={{ minWidth: 200 }}>
      {onClick ? <CardActionArea onClick={onClick}>{body}</CardActionArea> : body}
    </Card>
  )
}

function vulnerabilityValue(report: ReportSummary | undefined): ReactNode {
  if (!report || report.failed) return 'Unavailable'
  return `${num(report.vulnerable_package_count)} vulnerable`
}

function licenseValue(report: ReportSummary | undefined): ReactNode {
  if (!report || report.failed) return 'Unavailable'
  const copyleft = num(report['Strong Copyleft']) + num(report['Weak Copyleft'])
  return `${num(report['Permissive'])} permissive · ${copyleft} copyleft · ${num(report['Unknown'])} unknown`
}

function versionValue(report: ReportSummary | undefined): ReactNode {
  if (!report || report.failed) return 'Unavailable'
  const behind = num(report['behind-1']) + num(report['behind-2+'])
  return `${num(report['current'])} current · ${behind} behind · ${num(report['unknown'])} unknown`
}

export function OverviewTab({ status, onNavigate }: { status: JobStatus; onNavigate: (tabIndex: number) => void }) {
  const stats = status.summary_stats ?? {}
  const reports = stats.reports ?? {}
  const [exporting, setExporting] = useState(false)

  const anyReportAvailable =
    reportAvailable(reports.vuln) || reportAvailable(reports.license) || reportAvailable(reports.version)

  // Combined workbook: fetch the SBOM document plus the three full reports and compose a
  // sheet each, reusing the per-tab sheet builders (Stories 8.12–8.14, 8.27). The SBOM is
  // the core artifact, so its sheet leads (Story 8.27). A source that rejects is simply
  // omitted (AC #3) — the export still succeeds for the rest (Story 8.15).
  async function exportAll() {
    setExporting(true)
    try {
      const [sbom, versions, vulns, licenses] = await Promise.allSettled([
        getSbomDocument(status.task_id),
        getVersions(status.task_id),
        getVulnerabilities(status.task_id),
        getLicenses(status.task_id),
      ])
      const sheets: SheetSpec[] = []
      if (sbom.status === 'fulfilled') sheets.push(sbomComponentsSheet(sbom.value))
      if (versions.status === 'fulfilled') sheets.push(versionCurrencySheet(versions.value.packages))
      if (vulns.status === 'fulfilled') sheets.push(vulnerabilitiesSheet(vulns.value))
      if (licenses.status === 'fulfilled') sheets.push(licensesSheet(licenses.value))
      if (sheets.length > 0) await downloadWorkbook(buildWorkbook(sheets), 'sbom-report.xlsx')
    } finally {
      setExporting(false)
    }
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        {status.result_url ? (
          <Button variant="contained" href={status.result_url} startIcon={<DownloadActionIcon />}>
            Download SBOM{status.output_format ? ` (${status.output_format})` : ''}
          </Button>
        ) : (
          <Alert severity="warning">The SBOM artifact is not available for this job.</Alert>
        )}
        {anyReportAvailable && status.artifacts_available && (
          <Button variant="outlined" onClick={exportAll} disabled={exporting} startIcon={<ExportIcon />}>
            {exporting ? 'Exporting…' : 'Export all to Excel'}
          </Button>
        )}
      </Box>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
        <MetricCard title="Total packages" value={num(stats.total_packages)} />
        <MetricCard
          title="Vulnerabilities"
          value={vulnerabilityValue(reports.vuln)}
          onClick={() => onNavigate(TAB.vulnerabilities)}
        />
        <MetricCard title="Licenses" value={licenseValue(reports.license)} onClick={() => onNavigate(TAB.licenses)} />
        <MetricCard
          title="Version currency"
          value={versionValue(reports.version)}
          onClick={() => onNavigate(TAB.versions)}
        />
      </Box>
    </Box>
  )
}
