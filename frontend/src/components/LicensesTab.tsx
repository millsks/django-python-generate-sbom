// Licenses tab (Story 5.4): packages grouped into four legal-risk tiers (in the
// backend's descending-attention order), each an accordion that starts collapsed
// when empty. A failed phase shows the shared TabFailureNotice.
import { useEffect, useState } from 'react'
import Accordion from '@mui/material/Accordion'
import AccordionDetails from '@mui/material/AccordionDetails'
import AccordionSummary from '@mui/material/AccordionSummary'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Stack from '@mui/material/Stack'
import Link from '@mui/material/Link'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Typography from '@mui/material/Typography'
import { ApiError } from '../api/client'
import { getLicenses, type LicenseReport } from '../api/reports'
import { buildWorkbook, downloadWorkbook } from '../excelExport'
import { licensesSheet } from '../reportSheets'
import { TabFailureNotice } from './TabFailureNotice'

const SIGNALS: Record<string, string> = {
  'Strong Copyleft': 'Attention required',
  'Weak Copyleft': 'Review recommended',
  Unknown: 'Legal review needed',
  Permissive: 'Use freely',
}

// Default tier order: most legally-significant first (copyleft → unknown → permissive),
// with packages sorted by name within a tier (Story 8.16).
const TIER_RANK: Record<string, number> = { 'Strong Copyleft': 4, 'Weak Copyleft': 3, Unknown: 2, Permissive: 1 }
const byTierRank = (a: { tier: string }, b: { tier: string }) => (TIER_RANK[b.tier] ?? 0) - (TIER_RANK[a.tier] ?? 0)

export function LicensesTab({ taskId }: { taskId: string }) {
  const [report, setReport] = useState<LicenseReport | null>(null)
  const [failure, setFailure] = useState<{ reason: string | null } | null>(null)
  const [error, setError] = useState(false)
  // Controlled expanded state: the set of tier keys currently open. Initialized
  // to "tiers with packages expanded" once the report loads (Story 8.17).
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  useEffect(() => {
    let active = true
    getLicenses(taskId).then(
      (data) => {
        if (!active) return
        setReport(data)
        setExpanded(new Set(data.tiers.filter((tier) => tier.packages.length > 0).map((tier) => tier.tier)))
      },
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

  if (failure) return <TabFailureNotice reason={failure.reason} />
  if (error) return <Alert severity="error">Could not load the license report.</Alert>
  if (!report) return <CircularProgress aria-label="Loading licenses" />

  const toggleTier = (key: string) => (_event: unknown, isExpanded: boolean) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (isExpanded) next.add(key)
      else next.delete(key)
      return next
    })
  }
  const expandAll = () => setExpanded(new Set(report.tiers.map((tier) => tier.tier)))
  const collapseAll = () => setExpanded(new Set())
  const exportExcel = () => downloadWorkbook(buildWorkbook([licensesSheet(report)]), 'licenses.xlsx')

  return (
    <Box>
      {report.tiers.length > 0 && (
        <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
          <Button size="small" onClick={expandAll}>
            Expand all
          </Button>
          <Button size="small" onClick={collapseAll}>
            Collapse all
          </Button>
          <Button size="small" variant="outlined" onClick={exportExcel} sx={{ ml: 'auto' }}>
            Export to Excel
          </Button>
        </Stack>
      )}
      {[...report.tiers].sort(byTierRank).map((tier) => (
        <Accordion key={tier.tier} expanded={expanded.has(tier.tier)} onChange={toggleTier(tier.tier)}>
          <AccordionSummary expandIcon={<span aria-hidden>▾</span>}>
            <Typography sx={{ fontWeight: 600 }}>
              {tier.tier}
              {SIGNALS[tier.tier] ? ` — ${SIGNALS[tier.tier]}` : ''} ({tier.packages.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            {tier.packages.length === 0 ? (
              <Typography color="text.secondary">No packages in this tier.</Typography>
            ) : (
              <Table size="small" aria-label={`${tier.tier} packages`}>
                <TableHead>
                  <TableRow>
                    <TableCell>Package</TableCell>
                    <TableCell>Version</TableCell>
                    <TableCell>License</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {[...tier.packages]
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map((pkg) => (
                    <TableRow key={`${pkg.name}-${pkg.version}`}>
                      <TableCell>
                        <Link href={`https://pypi.org/project/${pkg.name}/`} target="_blank" rel="noopener">
                          {pkg.name}
                        </Link>
                      </TableCell>
                      <TableCell>{pkg.version}</TableCell>
                      <TableCell>{pkg.license}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  )
}
