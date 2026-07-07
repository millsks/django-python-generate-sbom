// SBOM viewer tab (Story 8.6): reads the generated SBOM in-app instead of only
// downloading it. Two views — a structured component table and the raw document
// text — toggled by a segmented control. Content comes from the inline document
// endpoint (AD-5); an unavailable/expired artifact shows a notice, not an error.
import { useEffect, useMemo, useState } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TableSortLabel from '@mui/material/TableSortLabel'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import Typography from '@mui/material/Typography'
import { ApiError } from '../api/client'
import { getSbomDocument, type SbomComponent, type SbomDocument } from '../api/sbom'

type View = 'components' | 'raw'

export function SbomTab({ taskId }: { taskId: string }) {
  const [doc, setDoc] = useState<SbomDocument | null>(null)
  const [unavailable, setUnavailable] = useState(false)
  const [error, setError] = useState(false)
  const [view, setView] = useState<View>('components')
  const [order, setOrder] = useState<'asc' | 'desc'>('asc')

  useEffect(() => {
    let active = true
    getSbomDocument(taskId).then(
      (data) => active && setDoc(data),
      (err: unknown) => {
        if (!active) return
        // A never-produced / expired artifact comes back as 404 (AD-2, Epic 7).
        if (err instanceof ApiError && err.status === 404) setUnavailable(true)
        else setError(true)
      },
    )
    return () => {
      active = false
    }
  }, [taskId])

  const showRelationship = useMemo(
    () => (doc?.components ?? []).some((c) => c.relationship),
    [doc],
  )

  const rows = useMemo(() => {
    if (!doc) return []
    const sorted = [...doc.components].sort((a, b) => a.name.localeCompare(b.name))
    return order === 'asc' ? sorted : sorted.reverse()
  }, [doc, order])

  // Provenance + document info shown above the table; absent fields are omitted (Story 8.11).
  const metadataRows = useMemo<[string, string][]>(() => {
    const meta = doc?.metadata
    if (!meta) return []
    const specLabel = meta.format && meta.spec_version ? `${meta.format} ${meta.spec_version}` : meta.format
    const entries: [string, string | undefined][] = [
      ['Component', meta.component_name],
      ['Application ID', meta.application_id],
      ['Repository', meta.repository_url],
      ['Branch', meta.source_branch],
      ['Format', specLabel],
      ['Generated', meta.generated],
    ]
    return entries.filter((entry): entry is [string, string] => Boolean(entry[1]))
  }, [doc])

  if (unavailable)
    return <Alert severity="info">The SBOM document is not available for this job (not generated or expired).</Alert>
  if (error) return <Alert severity="error">Could not load the SBOM document.</Alert>
  if (!doc) return <CircularProgress aria-label="Loading SBOM" />

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          {doc.components.length} components · {doc.format}
        </Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={view}
          onChange={(_e, next: View | null) => next && setView(next)}
          aria-label="SBOM view"
        >
          <ToggleButton value="components">Components</ToggleButton>
          <ToggleButton value="raw">Raw</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {view === 'components' ? (
        <>
          {metadataRows.length > 0 && (
            <Box
              component="dl"
              aria-label="SBOM metadata"
              sx={{
                display: 'grid',
                gridTemplateColumns: 'max-content 1fr',
                columnGap: 2,
                rowGap: 0.5,
                m: 0,
                mb: 2,
                p: 2,
                bgcolor: 'action.hover',
                borderRadius: 1,
                fontSize: '0.875rem',
              }}
            >
              {metadataRows.map(([label, value]) => (
                <Box key={label} sx={{ display: 'contents' }}>
                  <Box component="dt" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                    {label}
                  </Box>
                  <Box component="dd" sx={{ m: 0, wordBreak: 'break-word' }}>
                    {value}
                  </Box>
                </Box>
              ))}
            </Box>
          )}
          <TableContainer sx={{ maxHeight: 600 }}>
          <Table size="small" stickyHeader aria-label="sbom components">
            <TableHead>
              <TableRow>
                <TableCell sortDirection={order}>
                  <TableSortLabel
                    active
                    direction={order}
                    onClick={() => setOrder(order === 'asc' ? 'desc' : 'asc')}
                  >
                    Name
                  </TableSortLabel>
                </TableCell>
                <TableCell>Version</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>License</TableCell>
                {showRelationship && <TableCell>Relationship</TableCell>}
                <TableCell>Ecosystem</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row: SbomComponent) => (
                <TableRow key={`${row.name}@${row.version}`}>
                  <TableCell>{row.name}</TableCell>
                  <TableCell>{row.version || '—'}</TableCell>
                  <TableCell>{row.type ?? '—'}</TableCell>
                  <TableCell>{row.license ?? '—'}</TableCell>
                  {showRelationship && <TableCell>{row.relationship ?? '—'}</TableCell>}
                  <TableCell>{row.ecosystem ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        </>
      ) : (
        <Box
          component="pre"
          sx={{
            m: 0,
            p: 2,
            maxHeight: 600,
            overflow: 'auto',
            fontFamily: 'monospace',
            fontSize: '0.8rem',
            bgcolor: 'action.hover',
            borderRadius: 1,
          }}
        >
          {doc.raw}
        </Box>
      )}
    </Box>
  )
}
