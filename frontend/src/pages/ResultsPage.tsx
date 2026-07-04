// Results page shell (Story 5.1): tabs over a completed job's outputs, with a
// shareable URL (/results/:taskId), org access control, and a polling gate. The
// SBOM viewer sits second, right of Overview (Story 8.6).
import { useState } from 'react'
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
import { TERMINAL_STATUSES } from '../api/jobs'
import { useJobStatus } from '../hooks/useJobStatus'
import { OverviewTab } from '../components/OverviewTab'
import { SbomTab } from '../components/SbomTab'
import { VulnerabilitiesTab } from '../components/VulnerabilitiesTab'
import { LicensesTab } from '../components/LicensesTab'
import { DepGraph } from '../components/DepGraph'
import { VersionsTab } from '../components/VersionsTab'

const TAB_LABELS = ['Overview', 'SBOM', 'Vulnerabilities', 'Licenses', 'Dependency Graph', 'Version Currency']

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
  const { status, error: pageError } = useJobStatus(taskId)
  const [tab, setTab] = useState(0)

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
        <SbomTab taskId={taskId!} />
      </TabPanel>
      <TabPanel index={2} value={tab}>
        <VulnerabilitiesTab taskId={taskId!} totalPackages={status.summary_stats?.total_packages ?? 0} />
      </TabPanel>
      <TabPanel index={3} value={tab}>
        <LicensesTab taskId={taskId!} />
      </TabPanel>
      <TabPanel index={4} value={tab}>
        <DepGraph taskId={taskId!} />
      </TabPanel>
      <TabPanel index={5} value={tab}>
        <VersionsTab taskId={taskId!} />
      </TabPanel>
    </Container>
  )
}
