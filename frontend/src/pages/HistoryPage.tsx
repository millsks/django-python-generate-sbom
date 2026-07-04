// Dashboard: a paginated, filterable table of the org's SBOM jobs (Story 6.1).
// Static status per row; live polling of in-progress rows is Story 6.2.
import { useEffect, useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'
import Container from '@mui/material/Container'
import Link from '@mui/material/Link'
import MenuItem from '@mui/material/MenuItem'
import Pagination from '@mui/material/Pagination'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { listJobs, type JobListItem, type Paginated } from '../api/jobs'
import { JobStatusBadge } from '../components/JobStatusBadge'

const PAGE_SIZE = 25
const STATUS_OPTIONS = ['All', 'In Progress', 'Completed', 'Failed']
const FORMAT_OPTIONS = ['All', 'requirements', 'pyproject', 'pixi_lock', 'pixi_toml', 'conda']

export function HistoryPage() {
  const [data, setData] = useState<Paginated<JobListItem> | null>(null)
  const [error, setError] = useState(false)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('All')
  const [formatFilter, setFormatFilter] = useState('All')

  useEffect(() => {
    let active = true
    setData(null)
    listJobs({
      page,
      status: statusFilter,
      format: formatFilter === 'All' ? undefined : formatFilter,
    }).then(
      (result) => active && setData(result),
      () => active && setError(true),
    )
    return () => {
      active = false
    }
  }, [page, statusFilter, formatFilter])

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Your SBOM jobs
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <TextField
          select
          size="small"
          label="Status"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(1)
          }}
          sx={{ minWidth: 160 }}
        >
          {STATUS_OPTIONS.map((s) => (
            <MenuItem key={s} value={s}>
              {s}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          size="small"
          label="Manifest format"
          value={formatFilter}
          onChange={(e) => {
            setFormatFilter(e.target.value)
            setPage(1)
          }}
          sx={{ minWidth: 180 }}
        >
          {FORMAT_OPTIONS.map((f) => (
            <MenuItem key={f} value={f}>
              {f}
            </MenuItem>
          ))}
        </TextField>
      </Box>

      {error ? (
        <Alert severity="error">Could not load your jobs.</Alert>
      ) : !data ? (
        <CircularProgress aria-label="Loading jobs" />
      ) : data.count === 0 ? (
        <Alert severity="info">No jobs yet.</Alert>
      ) : (
        <>
          <TableContainer>
            <Table size="small" aria-label="jobs">
              <TableHead>
                <TableRow>
                  <TableCell>Submitted</TableCell>
                  <TableCell>Manifest</TableCell>
                  <TableCell>Format</TableCell>
                  <TableCell>Output</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Results</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.results.map((job) => (
                  <TableRow key={job.task_id}>
                    <TableCell>{new Date(job.created_at).toLocaleString()}</TableCell>
                    <TableCell>{job.manifest_filename}</TableCell>
                    <TableCell>{job.manifest_format}</TableCell>
                    <TableCell>{job.output_format}</TableCell>
                    <TableCell>
                      <JobStatusBadge status={job.status} />
                      {job.status === 'FAILED' && job.failure_reason && (
                        <Typography variant="caption" color="error" sx={{ display: 'block' }}>
                          {job.failure_reason}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Link component={RouterLink} to={`/results/${job.task_id}`}>
                        View
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <Pagination
              count={Math.ceil(data.count / PAGE_SIZE)}
              page={page}
              onChange={(_event, value) => setPage(value)}
            />
          </Box>
        </>
      )}
    </Container>
  )
}
