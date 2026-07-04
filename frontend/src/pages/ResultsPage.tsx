// Results page shell (Story 5.1): five tabs over a completed job's outputs, with
// a shareable URL (/results/:taskId), org access control, and a polling gate.
// Tab bodies (Vulnerabilities/Licenses/Graph/Versions) are filled by 5.2-5.6.
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'
import Container from '@mui/material/Container'
import LinearProgress from '@mui/material/LinearProgress'
import Tab from '@mui/material/Tab'
import Tabs from '@mui/material/Tabs'
import Typography from '@mui/material/Typography'
import { ApiError } from '../api/client'
import { getJobStatus, TERMINAL_STATUSES, type JobStatus } from '../api/jobs'
import { OverviewTab } from '../components/OverviewTab'
import { VulnerabilitiesTab } from '../components/VulnerabilitiesTab'
import { LicensesTab } from '../components/LicensesTab'
import { DepGraph } from '../components/DepGraph'

const TAB_LABELS = ['Overview', 'Vulnerabilities', 'Licenses', 'Dependency Graph', 'Version Currency']
const POLL_MS = 5000

function TabPanel({ index, value, children }: { index: number; value: number; children: ReactNode }) {
  return (
    <div role="tabpanel" hidden={value !== index} id={`results-tabpanel-${index}`}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

function Centered({ children }: { children: ReactNode }) {
  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      {children}
    </Container>
  )
}

export function ResultsPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const [status, setStatus] = useState<JobStatus | null>(null)
  const [pageError, setPageError] = useState<'denied' | 'error' | null>(null)
  const [tab, setTab] = useState(0)

  useEffect(() => {
    if (!taskId) return
    const id = taskId
    let active = true
    let timer = 0

    async function poll() {
      try {
        const next = await getJobStatus(id)
        if (!active) return
        setStatus(next)
        if (!TERMINAL_STATUSES.includes(next.status)) {
          timer = window.setTimeout(poll, POLL_MS)
        }
      } catch (err) {
        if (!active) return
        // Cross-org and unknown jobs both surface as 403/404 (no existence leak, AD-2).
        setPageError(err instanceof ApiError && (err.status === 403 || err.status === 404) ? 'denied' : 'error')
      }
    }

    void poll()
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [taskId])

  if (pageError === 'denied') {
    return (
      <Centered>
        <Alert severity="error">You don&apos;t have access to these results, or they don&apos;t exist.</Alert>
      </Centered>
    )
  }
  if (pageError === 'error') {
    return (
      <Centered>
        <Alert severity="error">Something went wrong loading these results. Please try again shortly.</Alert>
      </Centered>
    )
  }
  if (!status) {
    return (
      <Container maxWidth="sm" sx={{ py: 6, textAlign: 'center' }}>
        <CircularProgress aria-label="Loading results" />
      </Container>
    )
  }
  if (!TERMINAL_STATUSES.includes(status.status)) {
    return (
      <Centered>
        <Typography variant="h5" gutterBottom>
          Generating your SBOM…
        </Typography>
        <Typography color="text.secondary" gutterBottom>
          {status.current_phase || 'Starting'}
        </Typography>
        <LinearProgress variant="determinate" value={status.progress} />
      </Centered>
    )
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        SBOM Results
      </Typography>
      <Tabs value={tab} onChange={(_event, next: number) => setTab(next)} aria-label="results tabs">
        {TAB_LABELS.map((label) => (
          <Tab key={label} label={label} />
        ))}
      </Tabs>

      <TabPanel index={0} value={tab}>
        <OverviewTab status={status} onNavigate={setTab} />
      </TabPanel>
      <TabPanel index={1} value={tab}>
        <VulnerabilitiesTab taskId={taskId!} totalPackages={status.summary_stats?.total_packages ?? 0} />
      </TabPanel>
      <TabPanel index={2} value={tab}>
        <LicensesTab taskId={taskId!} />
      </TabPanel>
      <TabPanel index={3} value={tab}>
        <DepGraph taskId={taskId!} />
      </TabPanel>

      {TAB_LABELS.slice(4).map((label, i) => (
        <TabPanel key={label} index={i + 4} value={tab}>
          <Typography color="text.secondary">The {label} report will appear here.</Typography>
        </TabPanel>
      ))}
    </Container>
  )
}
