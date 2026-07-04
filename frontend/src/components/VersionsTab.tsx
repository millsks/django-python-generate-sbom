// Version Currency tab (Story 5.6): a table of installed vs. latest with a
// Current/Behind/Unknown badge. Most-outdated (behind-2+) surfaces first by
// default; the status column sorts by class rank. A failed phase shows the notice.
import { useEffect, useMemo, useState } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TableSortLabel from '@mui/material/TableSortLabel'
import { ApiError } from '../api/client'
import { getVersions, type VersionEntry, type VersionReport } from '../api/reports'
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

function compare(a: VersionEntry, b: VersionEntry, orderBy: Column): number {
  if (orderBy === 'currency') return (CURRENCY_RANK[a.currency] ?? 0) - (CURRENCY_RANK[b.currency] ?? 0)
  return String(a[orderBy] ?? '').localeCompare(String(b[orderBy] ?? ''))
}

export function VersionsTab({ taskId }: { taskId: string }) {
  const [report, setReport] = useState<VersionReport | null>(null)
  const [failure, setFailure] = useState<{ reason: string | null } | null>(null)
  const [error, setError] = useState(false)
  const [orderBy, setOrderBy] = useState<Column>('currency')
  const [order, setOrder] = useState<'asc' | 'desc'>('desc') // most-outdated first

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

  return (
    <Box>
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
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => {
              const b = badge(row.currency)
              return (
                <TableRow key={row.name}>
                  <TableCell>{row.name}</TableCell>
                  <TableCell>{row.installed}</TableCell>
                  <TableCell>{row.latest ?? '—'}</TableCell>
                  <TableCell>
                    <Chip size="small" label={b.label} color={b.color} />
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
