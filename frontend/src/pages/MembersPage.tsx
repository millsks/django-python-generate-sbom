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
import Typography from '@mui/material/Typography'
import { addMember, getMembers, removeMember, transferAdmin, type Member } from '../api/orgs'
import { useAuth } from '../auth/AuthProvider'
import { NoOrgState } from '../components/NoOrgState'
import { EmptyState, ErrorState, LoadingState } from '../components/PageState'
import { NavIcon } from '../icons'

export function MembersPage() {
  const { activeOrg } = useAuth()
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [isAdmin, setIsAdmin] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  function load() {
    getMembers()
      .then((response) => {
        setMembers(response.members)
        setIsAdmin(response.is_admin)
        setError(null)
      })
      .catch(() => setError('Failed to load members.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  async function handleAdd(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await addMember(email, password)
      setEmail('')
      setPassword('')
      load()
    } catch {
      setError('Could not add member — they may already belong to this org.')
    }
  }

  async function handleRemove(userId: number) {
    setError(null)
    try {
      await removeMember(userId)
      load()
    } catch {
      setError('Could not remove member.')
    }
  }

  async function handleTransfer(userId: number) {
    setError(null)
    try {
      await transferAdmin(userId)
      load()
    } catch {
      setError('Could not transfer admin.')
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
                        {member.role !== 'admin' && (
                          <Button size="small" onClick={() => handleTransfer(member.user_id)}>
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
          <Box
            component="form"
            onSubmit={handleAdd}
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
            <TextField
              size="small"
              label="Temp password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <Button type="submit" variant="contained">
              Add member
            </Button>
          </Box>
        </Paper>
      )}
    </Container>
  )
}
