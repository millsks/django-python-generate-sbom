// Version Currency tab (Story 5.6): a table of installed vs. latest with a
// Current/Behind/Unknown badge. Most-outdated (behind-2+) surfaces first by
// default; the status column sorts by class rank. A failed phase shows the notice.
import { useEffect, useMemo, useState } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Link from '@mui/material/Link'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TableSortLabel from '@mui/material/TableSortLabel'
import Typography from '@mui/material/Typography'
import { ApiError } from '../api/client'
import { getVersions, type VersionEntry, type VersionReport } from '../api/reports'
import { buildWorkbook, downloadWorkbook } from '../excelExport'
import { ecosystemLabel, registryUrl } from '../registryLinks'
import { versionCurrencySheet } from '../reportSheets'
import { TabFailureNotice } from './TabFailureNotice'

// Descending outdatedness: behind-2+ first, then behind-1, current, unknown.
const CURRENCY_RANK: Record<string, number> = { 'behind-2+': 3, 'behind-1': 2, current: 1, unknown: 0 }

type Column = 'name' | 'installed' | 'latest' | 'currency'
const COLUMNS: { key: Column; label: string }[] = [
  { key: 'name', label: 'Package' },
  { key: 'installed', label: 'Installed' },
  { key: 'latest', label: 'Latest' },
  { key: 'currency', label: 'Status' },
]

function badge(currency: string): { label: string; color: 'success' | 'warning' | 'default' } {
  if (currency === 'current') return { label: 'Current', color: 'success' }
  if (currency === 'unknown') return { label: 'Unknown', color: 'default' }
  return { label: currency === 'behind-2+' ? 'Behind 2+' : 'Behind 1', color: 'warning' }
}

// The LTS cell shows the tracked LTS series and whether the installed version is on
// it: green "On LTS (x.y)" when it is, an outlined "LTS x.y (target)" when it isn't,
// and a dash when no LTS is tracked for the package.
function LtsCell({ lts, onLts }: { lts: string | null; onLts: boolean | null }) {
  if (!lts) return <>—</>
  return onLts ? (
    <Chip size="small" label={`On LTS (${lts})`} color="success" />
  ) : (
    <Chip size="small" variant="outlined" color="info" label={`LTS ${lts} (target)`} />
  )
}

// The package name links to its registry detail page (PyPI project page or
// prefix.dev's conda-forge channel explorer); plain text when the ecosystem is
// unknown (Story 8.9).
function NameCell({ pkg }: { pkg: VersionEntry }) {
  const url = registryUrl({ name: pkg.name, version: pkg.installed, ecosystem: pkg.ecosystem })
  return url ? (
    <Link href={url} target="_blank" rel="noopener noreferrer">
      {pkg.name}
    </Link>
  ) : (
    <>{pkg.name}</>
  )
}

function SourceCell({ ecosystem }: { ecosystem?: string }) {
  const label = ecosystemLabel(ecosystem)
  return label ? <Chip size="small" variant="outlined" label={label} /> : <>—</>
}

// conda-forge latest (via prefix.dev). Rendered in an error color when it diverges
// from the PyPI latest, to flag that conda-forge is out of step (Story 8.10).
function CondaLatestCell({ condaLatest, mismatch }: { condaLatest?: string | null; mismatch?: boolean }) {
  if (!condaLatest) return <>—</>
  return mismatch ? (
    <Typography component="span" variant="body2" color="error" title="Differs from the PyPI latest">
      {condaLatest}
    </Typography>
  ) : (
    <>{condaLatest}</>
  )
}

function compare(a: VersionEntry, b: VersionEntry, orderBy: Column): number {
  if (orderBy === 'currency') return (CURRENCY_RANK[a.currency] ?? 0) - (CURRENCY_RANK[b.currency] ?? 0)
  return String(a[orderBy] ?? '').localeCompare(String(b[orderBy] ?? ''))
}

export function VersionsTab({ taskId }: { taskId: string }) {
  const [report, setReport] = useState<VersionReport | null>(null)
  const [failure, setFailure] = useState<{ reason: string | null } | null>(null)
  const [error, setError] = useState(false)
  const [orderBy, setOrderBy] = useState<Column>('name') // default: by package name (Story 8.16)
  const [order, setOrder] = useState<'asc' | 'desc'>('asc')

  useEffect(() => {
    let active = true
    getVersions(taskId).then(
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
    const sorted = [...report.packages].sort((a, b) => compare(a, b, orderBy))
    return order === 'asc' ? sorted : sorted.reverse()
  }, [report, orderBy, order])

  function sortBy(column: Column) {
    if (orderBy === column) setOrder(order === 'asc' ? 'desc' : 'asc')
    else {
      setOrderBy(column)
      setOrder('desc')
    }
  }

  if (failure) return <TabFailureNotice reason={failure.reason} />
  if (error) return <Alert severity="error">Could not load the version currency report.</Alert>
  if (!report) return <CircularProgress aria-label="Loading version currency" />
  if (report.packages.length === 0) return <Alert severity="info">No version data available.</Alert>

  const exportExcel = () =>
    downloadWorkbook(buildWorkbook([versionCurrencySheet(report.packages)]), 'version-currency.xlsx')

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
        <Button size="small" variant="outlined" onClick={exportExcel}>
          Export to Excel
        </Button>
      </Box>
      <TableContainer>
        <Table size="small" aria-label="version currency">
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
              <TableCell>conda-forge Latest</TableCell>
              <TableCell>LTS</TableCell>
              <TableCell>Source</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => {
              const b = badge(row.currency)
              return (
                <TableRow key={row.name}>
                  <TableCell>
                    <NameCell pkg={row} />
                  </TableCell>
                  <TableCell>{row.installed}</TableCell>
                  <TableCell>{row.latest ?? '—'}</TableCell>
                  <TableCell>
                    <Chip size="small" label={b.label} color={b.color} />
                  </TableCell>
                  <TableCell>
                    <CondaLatestCell condaLatest={row.conda_latest} mismatch={row.latest_mismatch} />
                  </TableCell>
                  <TableCell>
                    <LtsCell lts={row.lts} onLts={row.on_lts} />
                  </TableCell>
                  <TableCell>
                    <SourceCell ecosystem={row.ecosystem} />
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}
