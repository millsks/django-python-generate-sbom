// Shared "no active org" empty state (Story 2.6). Shown on the org-scoped pages when
// an authenticated user has no active organization, in place of an error or a redirect.
// Offers a create-org affordance that opens the reusable CreateOrgDialog.
import { useState } from 'react'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import { useAuth } from '../auth/AuthProvider'
import { EmptyState } from './PageState'
import { CreateOrgDialog } from './CreateOrgDialog'
import { AddActionIcon, NavIcon } from '../icons'

export const NO_ORG_MESSAGE = "You're not in an organization yet — create one or ask an admin to add you."

export function NoOrgState() {
  // Only global admins may create orgs (Story 2.12); everyone else waits to be added.
  const { isGlobalAdmin } = useAuth()
  const [open, setOpen] = useState(false)
  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <EmptyState
        icon={NavIcon.members}
        title="No organization yet"
        message={NO_ORG_MESSAGE}
        action={
          isGlobalAdmin ? (
            <Button variant="contained" startIcon={<AddActionIcon />} onClick={() => setOpen(true)}>
              Create organization
            </Button>
          ) : undefined
        }
      />
      {isGlobalAdmin && <CreateOrgDialog open={open} onClose={() => setOpen(false)} />}
    </Container>
  )
}
