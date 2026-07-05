import type { SvgIconComponent } from '@mui/icons-material'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Container from '@mui/material/Container'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { Link as RouterLink } from 'react-router-dom'
import { APP_NAME, DOCS_URL } from '../config'
import { ExportIcon, TabIcon, UploadActionIcon } from '../icons'

// The public landing page (Story 12.8) at `/`, rendered in the app shell for everyone
// (incl. anonymous visitors). Theme-aware and responsive; the "Upload a manifest" CTA
// points at a protected route, so ProtectedRoute sends anonymous users to login.

interface Feature {
  Icon: SvgIconComponent
  title: string
  blurb: string
}

const FEATURES: Feature[] = [
  { Icon: TabIcon.sbom, title: 'SBOM document', blurb: 'A standards-based CycloneDX/SPDX bill of materials — view it in-app or download it.' },
  { Icon: TabIcon.vulnerabilities, title: 'Vulnerability report', blurb: 'Known CVEs across your dependencies, ranked by severity.' },
  { Icon: TabIcon.licenses, title: 'License compliance', blurb: 'Every dependency’s license, surfaced for review.' },
  { Icon: TabIcon.graph, title: 'Dependency graph', blurb: 'Direct and transitive relationships, visualized.' },
  { Icon: TabIcon.versions, title: 'Version currency', blurb: 'How far behind each package is — latest on PyPI vs conda-forge.' },
  { Icon: ExportIcon, title: 'Excel export', blurb: 'Export any report to a formatted spreadsheet.' },
]

const STEPS: { title: string; blurb: string }[] = [
  { title: 'Upload a manifest', blurb: 'requirements.txt, pyproject.toml, or environment.yml.' },
  { title: 'Resolve & analyze', blurb: 'Dependencies are resolved and checked for vulnerabilities, licenses, and version currency.' },
  { title: 'Review the reports', blurb: 'Explore the SBOM, vulnerabilities, licenses, graph, and versions.' },
  { title: 'Export & share', blurb: 'Download the SBOM or export any report to Excel.' },
]

function FeatureCard({ Icon, title, blurb }: Feature) {
  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Icon color="primary" />
          <Typography variant="h6" component="h3">
            {title}
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary">
          {blurb}
        </Typography>
      </CardContent>
    </Card>
  )
}

export function HomePage() {
  return (
    <Container maxWidth="lg" sx={{ py: { xs: 4, md: 8 } }}>
      <Stack spacing={3} sx={{ textAlign: 'center', alignItems: 'center', mb: { xs: 6, md: 10 } }}>
        <Typography variant="h2" component="h1" sx={{ fontWeight: 700 }}>
          {APP_NAME}
        </Typography>
        <Typography variant="h5" component="p" color="text.secondary" sx={{ maxWidth: 720 }}>
          Generate Software Bills of Materials from Python dependency manifests.
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 640 }}>
          Upload a manifest and get a standards-based SBOM plus vulnerability, license, dependency-graph,
          and version-currency reports — all in one place.
        </Typography>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ pt: 1 }}>
          <Button component={RouterLink} to="/upload" variant="contained" size="large" startIcon={<UploadActionIcon />}>
            Upload a manifest
          </Button>
          <Button component="a" href={DOCS_URL} target="_blank" rel="noopener noreferrer" variant="outlined" size="large">
            Read the docs
          </Button>
        </Stack>
      </Stack>

      <Box component="section" sx={{ mb: { xs: 6, md: 10 } }}>
        <Typography variant="h4" component="h2" sx={{ fontWeight: 700, textAlign: 'center', mb: 4 }}>
          What you get
        </Typography>
        <Box
          sx={{
            display: 'grid',
            gap: 3,
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' },
          }}
        >
          {FEATURES.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </Box>
      </Box>

      <Box component="section">
        <Typography variant="h4" component="h2" sx={{ fontWeight: 700, textAlign: 'center', mb: 4 }}>
          How it works
        </Typography>
        <Box
          sx={{
            display: 'grid',
            gap: 3,
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
          }}
        >
          {STEPS.map((step, index) => (
            <Box key={step.title}>
              <Typography variant="h4" component="div" color="primary" sx={{ fontWeight: 700 }}>
                {index + 1}
              </Typography>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {step.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {step.blurb}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
    </Container>
  )
}
