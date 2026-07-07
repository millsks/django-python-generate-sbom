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
import { useAuth } from '../auth/AuthProvider'
import { useJobStatus } from '../hooks/useJobStatus'
import { NoOrgState } from '../components/NoOrgState'
import { OverviewTab } from '../components/OverviewTab'
import { SbomTab } from '../components/SbomTab'
import { VulnerabilitiesTab } from '../components/VulnerabilitiesTab'
import { LicensesTab } from '../components/LicensesTab'
import { VersionsTab } from '../components/VersionsTab'
import { TabIcon } from '../icons'

const TABS = [
  { label: 'Overview', Icon: TabIcon.overview },
  { label: 'SBOM', Icon: TabIcon.sbom },
  { label: 'Vulnerabilities', Icon: TabIcon.vulnerabilities },
  { label: 'Licenses', Icon: TabIcon.licenses },
  { label: 'Version Currency', Icon: TabIcon.versions },
] as const

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
  const { activeOrg } = useAuth()
  const { status, error: pageError } = useJobStatus(taskId)
  const [tab, setTab] = useState(0)

  if (!activeOrg) {
    return <NoOrgState />
  }
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

  // A completed job whose artifacts were cleaned (expiry sweep or manual delete):
  // the SBOM + reports are gone, but the summary metadata is retained (Story 7.3).
  // Distinct from a FAILED job (which shows its failure reason above).
  if (status.status === 'SUCCESS' && !status.artifacts_available) {
    const removedOn = status.artifacts_expire_at ? new Date(status.artifacts_expire_at).toLocaleDateString() : null
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          SBOM Results
        </Typography>
        <Alert severity="warning" sx={{ mb: 3 }}>
          The SBOM and analysis reports for this job are no longer available
          {removedOn ? ` — the stored artifacts were removed on ${removedOn}` : ''}. Only the job summary below is
          retained; downloads and per-report views are unavailable.
        </Alert>
        <OverviewTab status={status} onNavigate={() => {}} />
      </Container>
    )
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        SBOM Results
      </Typography>
      <Tabs
        value={tab}
        onChange={(_event, next: number) => setTab(next)}
        aria-label="results tabs"
        variant="scrollable"
        scrollButtons="auto"
      >
        {TABS.map(({ label, Icon }) => (
          <Tab key={label} label={label} icon={<Icon fontSize="small" />} iconPosition="start" />
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
        <VersionsTab taskId={taskId!} />
      </TabPanel>
    </Container>
  )
}
