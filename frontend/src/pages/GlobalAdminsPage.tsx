import { useEffect, useState, type FormEvent } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import Paper from '@mui/material/Paper'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { grantGlobalAdmin, listGlobalAdmins, revokeGlobalAdmin, type GlobalAdmin } from '../api/orgs'
import { ApiError } from '../api/client'
import { ErrorState, LoadingState } from '../components/PageState'

// Global-admin management screen (Story 13.1): list, grant-by-email, and revoke global
// admins. Reached only via GlobalAdminRoute + a global-admin-only nav item; the API is
// global-admin-gated too.
export function GlobalAdminsPage() {
  const [admins, setAdmins] = useState<GlobalAdmin[]>([])
  const [loading, setLoading] = useState(true)
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pendingRevoke, setPendingRevoke] = useState<GlobalAdmin | null>(null)

  function load() {
    listGlobalAdmins()
      .then((response) => {
        setAdmins(response.global_admins)
        setError(null)
      })
      .catch(() => setError('Failed to load global admins.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  async function handleGrant(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await grantGlobalAdmin(email)
      setEmail('')
      load()
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === 'no_such_user'
          ? 'No registered user with that email.'
          : 'Could not grant global admin.',
      )
    }
  }

  async function handleRevoke() {
    const target = pendingRevoke
    setPendingRevoke(null)
    if (!target) return
    setError(null)
    try {
      await revokeGlobalAdmin(target.user_id)
      load()
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === 'last_global_admin'
          ? 'There must always be at least one global admin.'
          : 'Could not revoke global admin.',
      )
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Global Admins
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Global admins are admins of every organization. Manage the platform-admin tier here.
      </Typography>

      {error && (
        <Box sx={{ mb: 2 }}>
          <ErrorState message={error} />
        </Box>
      )}

      {loading ? (
        <LoadingState label="Loading global admins" />
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table aria-label="global admins">
            <TableHead>
              <TableRow>
                <TableCell>Email</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {admins.map((admin) => (
                <TableRow key={admin.user_id} hover>
                  <TableCell>{admin.email}</TableCell>
                  <TableCell align="right">
                    <Button size="small" color="error" onClick={() => setPendingRevoke(admin)}>
                      Revoke
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Paper variant="outlined" sx={{ p: 2, mt: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Grant global admin
        </Typography>
        <Box
          component="form"
          onSubmit={handleGrant}
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
          <Button type="submit" variant="contained">
            Grant
          </Button>
        </Box>
      </Paper>

      <Dialog open={pendingRevoke !== null} onClose={() => setPendingRevoke(null)}>
        <DialogTitle>Revoke global admin?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {pendingRevoke?.email} will be removed from the platform-admin tier and demoted to a member of
            every organization.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingRevoke(null)}>Cancel</Button>
          <Button color="error" onClick={handleRevoke}>
            Revoke
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}
