// Vulnerabilities tab (Story 5.3): a sortable, severity-filterable table of
// vulnerable packages. Fetches the report JSON (served inline by the backend);
// a failed phase shows the shared TabFailureNotice, and a clean scan shows an
// explicit zero-state rather than an empty table.
import { useEffect, useMemo, useState } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Link from '@mui/material/Link'
import MenuItem from '@mui/material/MenuItem'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TableSortLabel from '@mui/material/TableSortLabel'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { ApiError } from '../api/client'
import { getVulnerabilities, type VulnerabilityReport } from '../api/reports'
import { buildWorkbook, downloadWorkbook } from '../excelExport'
import { ExportIcon, severityIcon } from '../icons'
import { vulnerabilitiesSheet } from '../reportSheets'
import { TabFailureNotice } from './TabFailureNotice'

// Severity cell: the shared severity icon + label (one vocabulary across the app).
function SeverityCell({ severity }: { severity: string }) {
  const { Icon, color } = severityIcon(severity)
  return (
    <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
      <Icon color={color} fontSize="small" titleAccess={severity} />
      {severity}
    </Box>
  )
}

const SEVERITY_RANK: Record<string, number> = { Critical: 4, High: 3, Medium: 2, Low: 1, Unknown: 0 }
const SEVERITIES = ['Critical', 'High', 'Medium', 'Low', 'Unknown']

interface Row {
  name: string
  version: string
  ids: string
  cvss: number | null
  severity: string
  advisory: string
}

type Column = 'name' | 'version' | 'ids' | 'cvss' | 'severity'
const COLUMNS: { key: Column; label: string }[] = [
  { key: 'name', label: 'Package' },
  { key: 'version', label: 'Version' },
  { key: 'ids', label: 'CVE / GHSA' },
  { key: 'cvss', label: 'CVSS' },
  { key: 'severity', label: 'Severity' },
]

function toRows(report: VulnerabilityReport): Row[] {
  return report.packages.flatMap((pkg) =>
    pkg.vulnerabilities.map((v) => ({
      name: pkg.name,
      version: pkg.version,
      ids: [...new Set([v.id, ...v.aliases])].join(', '),
      cvss: v.cvss_score,
      severity: v.severity,
      advisory: v.advisory_url,
    })),
  )
}

function compare(a: Row, b: Row, orderBy: Column): number {
  if (orderBy === 'severity') return (SEVERITY_RANK[a.severity] ?? 0) - (SEVERITY_RANK[b.severity] ?? 0)
  if (orderBy === 'cvss') return (a.cvss ?? -1) - (b.cvss ?? -1)
  return String(a[orderBy]).localeCompare(String(b[orderBy]))
}

export function VulnerabilitiesTab({ taskId, totalPackages }: { taskId: string; totalPackages: number }) {
  const [report, setReport] = useState<VulnerabilityReport | null>(null)
  const [failure, setFailure] = useState<{ reason: string | null } | null>(null)
  const [error, setError] = useState(false)
  const [orderBy, setOrderBy] = useState<Column>('severity')
  const [order, setOrder] = useState<'asc' | 'desc'>('desc')
  const [severity, setSeverity] = useState('All')

  useEffect(() => {
    let active = true
    getVulnerabilities(taskId).then(
      (data) => active && setReport(data),
      (err: unknown) => {
        if (!active) return
        if (err instanceof ApiError && err.code === 'report_failed') setFailure({ reason: err.failureReason ?? null })
        else setError(true)
      },
    )
    return () => {
      active = false
    }
  }, [taskId])

  const rows = useMemo(() => {
    if (!report) return []
    const filtered = severity === 'All' ? toRows(report) : toRows(report).filter((r) => r.severity === severity)
    const sorted = [...filtered].sort((a, b) => compare(a, b, orderBy))
    return order === 'asc' ? sorted : sorted.reverse()
  }, [report, orderBy, order, severity])

  function sortBy(column: Column) {
    if (orderBy === column) setOrder(order === 'asc' ? 'desc' : 'asc')
    else {
      setOrderBy(column)
      setOrder('desc')
    }
  }

  if (failure) return <TabFailureNotice reason={failure.reason} />
  if (error) return <Alert severity="error">Could not load the vulnerability report.</Alert>
  if (!report) return <CircularProgress aria-label="Loading vulnerabilities" />

  if (report.packages.length === 0) {
    return <Alert severity="success">No vulnerabilities found in {totalPackages} packages.</Alert>
  }

  // Export covers the FULL report (all severities), independent of the active filter.
  const exportExcel = () => downloadWorkbook(buildWorkbook([vulnerabilitiesSheet(report)]), 'vulnerabilities.xlsx')

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
        <TextField
          select
          size="small"
          label="Severity"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          sx={{ maxWidth: 200 }}
        >
          <MenuItem value="All">All</MenuItem>
          {SEVERITIES.map((s) => (
            <MenuItem key={s} value={s}>
              {s}
            </MenuItem>
          ))}
        </TextField>
        <Button size="small" variant="outlined" onClick={exportExcel} startIcon={<ExportIcon />}>
          Export to Excel
        </Button>
      </Box>

      <TableContainer>
        <Table size="small" aria-label="vulnerabilities">
          <TableHead>
            <TableRow>
              {COLUMNS.map((col) => (
                <TableCell key={col.key} sortDirection={orderBy === col.key ? order : false}>
                  <TableSortLabel
                    active={orderBy === col.key}
                    direction={orderBy === col.key ? order : 'asc'}
                    onClick={() => sortBy(col.key)}
                  >
                    {col.label}
                  </TableSortLabel>
                </TableCell>
              ))}
              <TableCell>Advisory</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, i) => (
              <TableRow key={`${row.name}-${row.ids}-${i}`}>
                <TableCell>{row.name}</TableCell>
                <TableCell>{row.version}</TableCell>
                <TableCell>{row.ids}</TableCell>
                <TableCell>{row.cvss ?? '—'}</TableCell>
                <TableCell>
                  <SeverityCell severity={row.severity} />
                </TableCell>
                <TableCell>
                  <Link href={row.advisory} target="_blank" rel="noopener">
                    View
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Typography variant="caption" color="text.secondary">
        {report.summary.vulnerable_package_count} vulnerable package(s) of {totalPackages} scanned.
      </Typography>
    </Box>
  )
}
