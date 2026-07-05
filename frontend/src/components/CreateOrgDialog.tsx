// Reusable create-organization dialog (Story 2.6). A user with no active org (or one
// wanting an additional org — Story 2.5) opens this to create one; on success it
// switches into the new org and reloads so the whole app picks up the new context,
// matching the OrgSwitcher's switch-then-reload pattern.
import { useState, type FormEvent } from 'react'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import TextField from '@mui/material/TextField'
import { createOrg, switchOrg } from '../api/orgs'
import { ErrorState } from './PageState'

export function CreateOrgDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const org = await createOrg(name)
      await switchOrg(org.slug)
      window.location.reload()
    } catch {
      setError('Could not create the organization. Try a different name.')
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <form onSubmit={handleSubmit}>
        <DialogTitle>Create an organization</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          {error && <ErrorState message={error} />}
          <TextField
            autoFocus
            label="Organization name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" variant="contained" disabled={submitting || name.trim() === ''}>
            {submitting ? 'Creating…' : 'Create'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
