import { useEffect, useState, type FormEvent } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { addMember, getMembers, removeMember, transferAdmin, type Member } from '../api/orgs'

export function MembersPage() {
  const [members, setMembers] = useState<Member[]>([])
  const [isAdmin, setIsAdmin] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  function load() {
    getMembers()
      .then((response) => {
        setMembers(response.members)
        setIsAdmin(response.is_admin)
      })
      .catch(() => setError('Failed to load members.'))
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

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Members
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Email</TableCell>
            <TableCell>Role</TableCell>
            <TableCell>Joined</TableCell>
            {isAdmin && <TableCell>Actions</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {members.map((member) => (
            <TableRow key={member.user_id}>
              <TableCell>{member.email}</TableCell>
              <TableCell>{member.role}</TableCell>
              <TableCell>{new Date(member.joined_at).toLocaleDateString()}</TableCell>
              {isAdmin && (
                <TableCell>
                  <Button size="small" onClick={() => handleRemove(member.user_id)}>
                    Remove
                  </Button>
                  {member.role !== 'admin' && (
                    <Button size="small" onClick={() => handleTransfer(member.user_id)}>
                      Make admin
                    </Button>
                  )}
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {isAdmin && (
        <Box
          component="form"
          onSubmit={handleAdd}
          sx={{ display: 'flex', gap: 2, mt: 3, alignItems: 'center' }}
        >
          <TextField
            size="small"
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
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
      )}
    </Container>
  )
}
