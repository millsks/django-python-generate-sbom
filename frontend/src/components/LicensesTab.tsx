// Licenses tab (Story 5.4): packages grouped into four legal-risk tiers (in the
// backend's descending-attention order), each an accordion that starts collapsed
// when empty. A failed phase shows the shared TabFailureNotice.
import { useEffect, useState } from 'react'
import Accordion from '@mui/material/Accordion'
import AccordionDetails from '@mui/material/AccordionDetails'
import AccordionSummary from '@mui/material/AccordionSummary'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'
import Link from '@mui/material/Link'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Typography from '@mui/material/Typography'
import { ApiError } from '../api/client'
import { getLicenses, type LicenseReport } from '../api/reports'
import { TabFailureNotice } from './TabFailureNotice'

const SIGNALS: Record<string, string> = {
  'Strong Copyleft': 'Attention required',
  'Weak Copyleft': 'Review recommended',
  Unknown: 'Legal review needed',
  Permissive: 'Use freely',
}

export function LicensesTab({ taskId }: { taskId: string }) {
  const [report, setReport] = useState<LicenseReport | null>(null)
  const [failure, setFailure] = useState<{ reason: string | null } | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    getLicenses(taskId).then(
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

  if (failure) return <TabFailureNotice reason={failure.reason} />
  if (error) return <Alert severity="error">Could not load the license report.</Alert>
  if (!report) return <CircularProgress aria-label="Loading licenses" />

  return (
    <Box>
      {report.tiers.map((tier) => (
        <Accordion key={tier.tier} defaultExpanded={tier.packages.length > 0}>
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
                  {tier.packages.map((pkg) => (
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
