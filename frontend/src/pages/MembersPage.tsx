import { useEffect, useState, type FormEvent } from 'react'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import Typography from '@mui/material/Typography'
import {
  addMember,
  createMemberUser,
  demoteAdmin,
  getMembers,
  promoteAdmin,
  removeMember,
  type Member,
} from '../api/orgs'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { NoOrgState } from '../components/NoOrgState'
import { EmptyState, ErrorState, LoadingState } from '../components/PageState'
import { NavIcon } from '../icons'

// Specific, action-appropriate copy for each membership-error code the backend can
// return (Story 2.20). Every membership action maps the ApiError.code through this so
// the page shows the real reason (e.g. why a global admin or the last admin can't be
// touched) instead of a generic "Could not …". An action may override a code's copy
// (e.g. demote's global-admin wording); an unmapped code falls back to err.message.
const MEMBERSHIP_ERROR_COPY: Record<string, string> = {
  global_admin_protected:
    "This user is a global admin and can't be removed from a single org — revoke their global-admin status first.",
  last_admin: 'The organization must keep at least one admin.',
  admin_org_protected: 'The system admin org must always have at least one global admin.',
  not_a_member: 'That user is no longer a member of this org.',
  no_such_user: 'No registered user with that email. Use "Create new user" to provision an account.',
  already_member: 'That user is already a member of this org.',
  email_taken: 'A user with that email already exists — add them as an existing member instead.',
}

function membershipErrorMessage(err: unknown, fallback: string, overrides: Record<string, string> = {}): string {
  if (err instanceof ApiError) {
    const copy = { ...MEMBERSHIP_ERROR_COPY, ...overrides }
    if (err.code && copy[err.code]) return copy[err.code]
    return err.message
  }
  return fallback
}

export function MembersPage() {
  // The page is admin-only (AdminRoute), so isAdmin comes straight from useAuth.
  const { activeOrg, isAdmin } = useAuth()
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState<'existing' | 'create'>('existing')
  const [error, setError] = useState<string | null>(null)

  function load() {
    getMembers()
      .then((response) => {
        setMembers(response.members)
        setError(null)
      })
      .catch(() => setError('Failed to load members.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      if (mode === 'create') {
        await createMemberUser(email, password)
      } else {
        await addMember(email)
      }
      setEmail('')
      setPassword('')
      load()
    } catch (err) {
      setError(membershipErrorMessage(err, mode === 'create' ? 'Could not create the user.' : 'Could not add member.'))
    }
  }

  async function handleRemove(userId: number) {
    setError(null)
    try {
      await removeMember(userId)
      load()
    } catch (err) {
      setError(membershipErrorMessage(err, 'Could not remove member.'))
    }
  }

  async function handlePromote(userId: number) {
    setError(null)
    try {
      await promoteAdmin(userId)
      load()
    } catch (err) {
      setError(membershipErrorMessage(err, 'Could not make admin.'))
    }
  }

  async function handleDemote(userId: number) {
    setError(null)
    try {
      await demoteAdmin(userId)
      load()
    } catch (err) {
      setError(
        membershipErrorMessage(err, 'Could not make member.', {
          global_admin_protected: "Global admins can't be demoted.",
        }),
      )
    }
  }

  if (!activeOrg) {
    return <NoOrgState />
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Members
      </Typography>

      {error && (
        <Box sx={{ mb: 2 }}>
          <ErrorState message={error} />
        </Box>
      )}

      {loading ? (
        <LoadingState label="Loading members" />
      ) : members.length === 0 ? (
        <EmptyState icon={NavIcon.members} title="No members yet" message="Invite teammates to your organization below." />
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table aria-label="members">
            <TableHead>
              <TableRow>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Joined</TableCell>
                {isAdmin && <TableCell align="right">Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {members.map((member) => (
                <TableRow key={member.user_id} hover>
                  <TableCell>{member.email}</TableCell>
                  <TableCell>{member.role}</TableCell>
                  <TableCell>{new Date(member.joined_at).toLocaleDateString()}</TableCell>
                  {isAdmin && (
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                        <Button size="small" onClick={() => handleRemove(member.user_id)}>
                          Remove
                        </Button>
                        {member.role === 'admin' ? (
                          <Button size="small" onClick={() => handleDemote(member.user_id)}>
                            Make member
                          </Button>
                        ) : (
                          <Button size="small" onClick={() => handlePromote(member.user_id)}>
                            Make admin
                          </Button>
                        )}
                      </Box>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {isAdmin && (
        <Paper variant="outlined" sx={{ p: 2, mt: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Add a member
          </Typography>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={mode}
            onChange={(_event, next: 'existing' | 'create' | null) => {
              if (next) {
                setMode(next)
                setError(null)
              }
            }}
            aria-label="add member mode"
            sx={{ mb: 2 }}
          >
            <ToggleButton value="existing">Add existing</ToggleButton>
            <ToggleButton value="create">Create new user</ToggleButton>
          </ToggleButtonGroup>
          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 2, alignItems: { sm: 'center' } }}
          >
            <TextField
              size="small"
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              sx={{ flexGrow: 1 }}
            />
            {mode === 'create' && (
              <TextField
                size="small"
                label="Temp password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                slotProps={{ htmlInput: { minLength: 8 } }}
                sx={{ flexGrow: 1 }}
              />
            )}
            <Button type="submit" variant="contained">
              {mode === 'create' ? 'Create user' : 'Add member'}
            </Button>
          </Box>
          {mode === 'create' && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Creates a new account with this temporary password — share it with the new member out of band.
            </Typography>
          )}
        </Paper>
      )}
    </Container>
  )
}
