// Org maintenance control center (Story 2.11): one admin-facing place that gathers the
// org-administration destinations (members, API keys, create org) instead of scattered
// links. It composes the existing management pages by linking to them rather than
// duplicating their logic.
import { useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardActions from '@mui/material/CardActions'
import CardContent from '@mui/material/CardContent'
import Container from '@mui/material/Container'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { useAuth } from '../auth/AuthProvider'
import { CreateOrgDialog } from '../components/CreateOrgDialog'
import { NoOrgState } from '../components/NoOrgState'
import { AddActionIcon, NavIcon } from '../icons'

export function OrganizationPage() {
  const { activeOrg } = useAuth()
  const [createOpen, setCreateOpen] = useState(false)

  if (!activeOrg) {
    return <NoOrgState />
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Organization
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Manage {activeOrg.name}.
      </Typography>

      <Stack spacing={2}>
        <Card variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <NavIcon.members fontSize="small" />
              <Typography variant="h6">Members</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              Add existing users by email, create new user accounts, remove members, and transfer admin.
            </Typography>
          </CardContent>
          <CardActions>
            <Button component={RouterLink} to="/members">
              Manage members
            </Button>
          </CardActions>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <NavIcon.keys fontSize="small" />
              <Typography variant="h6">API keys</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              Create and revoke API keys scoped to this organization.
            </Typography>
          </CardContent>
          <CardActions>
            <Button component={RouterLink} to="/keys">
              Manage API keys
            </Button>
          </CardActions>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <NavIcon.organization fontSize="small" />
              <Typography variant="h6">New organization</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              Create another organization and switch into it.
            </Typography>
          </CardContent>
          <CardActions>
            <Button startIcon={<AddActionIcon />} onClick={() => setCreateOpen(true)}>
              Create organization
            </Button>
          </CardActions>
        </Card>
      </Stack>

      <CreateOrgDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </Container>
  )
}
