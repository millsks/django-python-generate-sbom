// Overview tab (Story 5.2): at-a-glance summary cards sourced entirely from the
// job's summary_stats (no per-report fetch — NFR-2.2), a SBOM download, and
// deep-links into the detail tabs. A metric backed by a failed phase shows
// "Unavailable" rather than a misleading 0 (FR-6.7).
import type { ReactNode } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardActionArea from '@mui/material/CardActionArea'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import type { JobStatus, ReportSummary } from '../api/jobs'

// Tab indices in the shell's fixed order (5.1).
const TAB = { vulnerabilities: 1, licenses: 2, versions: 4 }

const num = (value: unknown): number => (typeof value === 'number' ? value : 0)

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

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        {status.result_url ? (
          <Button variant="contained" href={status.result_url}>
            Download SBOM{status.output_format ? ` (${status.output_format})` : ''}
          </Button>
        ) : (
          <Alert severity="warning">The SBOM artifact is not available for this job.</Alert>
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
