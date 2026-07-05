// Visual status indicator for a job row (Story 6.1). Icon vocabulary: Story 12.2.
import Chip from '@mui/material/Chip'
import { jobStatusIcon } from '../icons'

const MAP: Record<string, { label: string; color: 'default' | 'info' | 'success' | 'error' }> = {
  PENDING: { label: 'In Progress', color: 'info' },
  PROGRESS: { label: 'In Progress', color: 'info' },
  SUCCESS: { label: 'Completed', color: 'success' },
  FAILED: { label: 'Failed', color: 'error' },
}

export function JobStatusBadge({ status }: { status: string }) {
  const { label, color } = MAP[status] ?? { label: status, color: 'default' }
  const { Icon } = jobStatusIcon(status)
  return <Chip size="small" label={label} color={color} icon={<Icon fontSize="small" />} />
}
