// Dashboard: a paginated, filterable table of the org's SBOM jobs (Story 6.1).
// In-progress rows auto-refresh via the shared useJobStatus hook (Story 6.2).
// Artifacts can be deleted per-job or in bulk (org-wide, admin) on demand (Story 7.2).
import { useEffect, useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Checkbox from '@mui/material/Checkbox'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Container from '@mui/material/Container'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import IconButton from '@mui/material/IconButton'
import LinearProgress from '@mui/material/LinearProgress'
import Link from '@mui/material/Link'
import MenuItem from '@mui/material/MenuItem'
import Pagination from '@mui/material/Pagination'
import Stack from '@mui/material/Stack'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import {
  bulkDeleteArtifacts,
  deleteJobArtifacts,
  listJobs,
  TERMINAL_STATUSES,
  type JobListItem,
  type Paginated,
} from '../api/jobs'
import { useAuth } from '../auth/AuthProvider'
import { JobStatusBadge } from '../components/JobStatusBadge'
import { formatDuration } from '../duration'
import { useJobStatus } from '../hooks/useJobStatus'
import { DeleteActionIcon } from '../icons'

const PAGE_SIZE = 25
const STATUS_OPTIONS = ['All', 'In Progress', 'Completed', 'Failed']
const FORMAT_OPTIONS = ['All', 'requirements', 'pyproject', 'pixi_lock', 'pixi_toml', 'conda']

// What a pending confirmation will delete once the user accepts.
type Confirm = { kind: 'single'; taskId: string } | { kind: 'selected' } | { kind: 'org' }

// One table row. Rows that start non-terminal poll live progress and swap to
// their final state in place when the job completes or fails (Story 6.2).
function JobRow({
  job,
  checked,
  onToggle,
  onDelete,
}: {
  job: JobListItem
  checked: boolean
  onToggle: (taskId: string) => void
  onDelete: (taskId: string) => void
}) {
  const { status: live } = useJobStatus(job.task_id, {
    enabled: !TERMINAL_STATUSES.includes(job.status),
  })
  const status = live?.status ?? job.status
  const failureReason = live?.failure_reason ?? job.failure_reason
  const inProgress = !TERMINAL_STATUSES.includes(status)
  // A completed job whose artifacts were cleaned (expiry sweep or manual delete):
  // record + metadata are kept, but there's nothing left to download or delete (Story 7.3).
  const artifactsAvailable = live?.artifacts_available ?? job.artifacts_available
  const expired = status === 'SUCCESS' && !artifactsAvailable

  // Elapsed: the serialized value for jobs already finished at list time; the live
  // completion for jobs that finish while polling; and a live created→now duration
  // (refreshed each 5s poll) for still-running jobs (Story 6.3).
  const createdMs = new Date(job.created_at).getTime()
  const elapsedSeconds =
    job.elapsed_seconds != null
      ? job.elapsed_seconds
      : live?.completed_at
        ? (new Date(live.completed_at).getTime() - createdMs) / 1000
        : inProgress
          ? (Date.now() - createdMs) / 1000
          : null

  return (
    <TableRow selected={checked}>
      <TableCell padding="checkbox">
        <Checkbox
          checked={checked}
          onChange={() => onToggle(job.task_id)}
          slotProps={{ input: { 'aria-label': `Select ${job.manifest_filename}` } }}
        />
      </TableCell>
      <TableCell>{new Date(job.created_at).toLocaleString()}</TableCell>
      <TableCell>{job.manifest_filename}</TableCell>
      <TableCell>{job.manifest_format}</TableCell>
      <TableCell>{job.output_format}</TableCell>
      <TableCell>
        <JobStatusBadge status={status} />
        {inProgress && live && (
          <Box sx={{ mt: 0.5, minWidth: 120 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
              {live.current_phase || 'Starting'} — {live.progress}%
            </Typography>
            <LinearProgress variant="determinate" value={live.progress} />
          </Box>
        )}
        {status === 'FAILED' && failureReason && (
          <Typography variant="caption" color="error" sx={{ display: 'block' }}>
            {failureReason}
          </Typography>
        )}
        {expired && (
          <Tooltip
            title={
              job.artifacts_expire_at
                ? `Stored artifacts removed (expiry ${new Date(job.artifacts_expire_at).toLocaleDateString()})`
                : 'Stored artifacts removed'
            }
          >
            <Chip
              size="small"
              color="warning"
              variant="outlined"
              label="Artifacts removed"
              sx={{ mt: 0.5, width: 'fit-content' }}
            />
          </Tooltip>
        )}
      </TableCell>
      <TableCell>{formatDuration(elapsedSeconds)}</TableCell>
      <TableCell>
        <Link component={RouterLink} to={`/results/${job.task_id}`}>
          View
        </Link>
      </TableCell>
      <TableCell padding="checkbox">
        <Tooltip title={expired ? 'Artifacts already removed' : 'Delete artifacts'}>
          <span>
            <IconButton
              size="small"
              color="error"
              aria-label={`Delete artifacts for ${job.manifest_filename}`}
              onClick={() => onDelete(job.task_id)}
              disabled={expired}
            >
              <DeleteActionIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      </TableCell>
    </TableRow>
  )
}

export function HistoryPage() {
  const { isAdmin } = useAuth()
  const [data, setData] = useState<Paginated<JobListItem> | null>(null)
  const [error, setError] = useState(false)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('All')
  const [formatFilter, setFormatFilter] = useState('All')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [confirm, setConfirm] = useState<Confirm | null>(null)
  const [busy, setBusy] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

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
  }, [page, statusFilter, formatFilter, refreshKey])

  function toggle(taskId: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(taskId)) next.delete(taskId)
      else next.add(taskId)
      return next
    })
  }

  function toggleAll() {
    const ids = data?.results.map((j) => j.task_id) ?? []
    setSelected((prev) => (ids.every((id) => prev.has(id)) ? new Set() : new Set(ids)))
  }

  async function runDelete() {
    if (!confirm) return
    setBusy(true)
    try {
      if (confirm.kind === 'single') await deleteJobArtifacts(confirm.taskId)
      else if (confirm.kind === 'selected') await bulkDeleteArtifacts({ taskIds: [...selected] })
      else await bulkDeleteArtifacts({ all: true })
      setSelected(new Set())
      setRefreshKey((k) => k + 1)
    } catch {
      setError(true)
    } finally {
      setBusy(false)
      setConfirm(null)
    }
  }

  const pageIds = data?.results.map((j) => j.task_id) ?? []
  const allChecked = pageIds.length > 0 && pageIds.every((id) => selected.has(id))
  const someChecked = pageIds.some((id) => selected.has(id)) && !allChecked

  const confirmText =
    confirm?.kind === 'org'
      ? "Delete the stored artifacts for ALL of your organization's jobs? The job records and their metadata are kept — only the SBOM and analysis-report files are removed. This cannot be undone."
      : confirm?.kind === 'selected'
        ? `Delete the stored artifacts for the ${selected.size} selected job(s)? The job records are kept; only the SBOM and report files are removed.`
        : 'Delete the stored artifacts for this job? The job record is kept; only the SBOM and report files are removed.'

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Your SBOM jobs
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2, alignItems: 'center' }}>
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
        <Box sx={{ flexGrow: 1 }} />
        <Stack direction="row" spacing={1}>
          <Button
            size="small"
            color="error"
            variant="outlined"
            startIcon={<DeleteActionIcon />}
            disabled={selected.size === 0}
            onClick={() => setConfirm({ kind: 'selected' })}
          >
            Delete selected ({selected.size})
          </Button>
          {isAdmin && (
            <Button
              size="small"
              color="error"
              variant="contained"
              startIcon={<DeleteActionIcon />}
              onClick={() => setConfirm({ kind: 'org' })}
            >
              Delete all artifacts
            </Button>
          )}
        </Stack>
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
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={allChecked}
                      indeterminate={someChecked}
                      onChange={toggleAll}
                      slotProps={{ input: { 'aria-label': 'Select all jobs on this page' } }}
                    />
                  </TableCell>
                  <TableCell>Submitted</TableCell>
                  <TableCell>Manifest</TableCell>
                  <TableCell>Format</TableCell>
                  <TableCell>Output</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Elapsed</TableCell>
                  <TableCell>Results</TableCell>
                  <TableCell padding="checkbox" />
                </TableRow>
              </TableHead>
              <TableBody>
                {data.results.map((job) => (
                  <JobRow
                    key={job.task_id}
                    job={job}
                    checked={selected.has(job.task_id)}
                    onToggle={toggle}
                    onDelete={(taskId) => setConfirm({ kind: 'single', taskId })}
                  />
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

      <Dialog open={confirm !== null} onClose={() => !busy && setConfirm(null)}>
        <DialogTitle>Delete artifacts?</DialogTitle>
        <DialogContent>
          <DialogContentText>{confirmText}</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirm(null)} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={runDelete} color="error" variant="contained" disabled={busy}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}
