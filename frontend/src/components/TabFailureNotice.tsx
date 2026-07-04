// Shared per-tab failure notice (FR-4.5 / FR-6.7). A failed analysis phase leaves
// the SBOM and other tabs usable; the affected tab renders this instead of content.
import Alert from '@mui/material/Alert'
import AlertTitle from '@mui/material/AlertTitle'

export function TabFailureNotice({ reason }: { reason: string | null }) {
  return (
    <Alert severity="warning">
      <AlertTitle>This report could not be generated</AlertTitle>
      {reason
        ? `Reason: ${reason}. The SBOM download and other reports remain available.`
        : 'The analysis phase failed. The SBOM download and other reports remain available.'}
    </Alert>
  )
}
