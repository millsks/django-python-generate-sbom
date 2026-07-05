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
import { createKey, getKeys, revokeKey, type ApiKey } from '../api/keys'
import { useAuth } from '../auth/AuthProvider'
import { NoOrgState } from '../components/NoOrgState'
import { EmptyState, ErrorState, LoadingState } from '../components/PageState'
import { AddActionIcon, DeleteActionIcon, NavIcon } from '../icons'

export function KeysPage() {
  // API Keys is viewable by any member; admin flag (create/revoke) comes from useAuth.
  const { activeOrg, isAdmin } = useAuth()
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [plaintext, setPlaintext] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  function load() {
    getKeys()
      .then((result) => {
        setKeys(result)
        setError(null)
      })
      .catch(() => setError('Failed to load API keys.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const created = await createKey(name)
      setPlaintext(created.key)
      setName('')
      load()
    } catch {
      setError('Could not create key — you may have reached the 10-key limit.')
    }
  }

  async function handleRevoke(id: string) {
    setError(null)
    try {
      await revokeKey(id)
      load()
    } catch {
      setError('Could not revoke key.')
    }
  }

  if (!activeOrg) {
    return <NoOrgState />
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        API keys
      </Typography>

      {error && (
        <Box sx={{ mb: 2 }}>
          <ErrorState message={error} />
        </Box>
      )}

      {loading ? (
        <LoadingState label="Loading API keys" />
      ) : keys.length === 0 ? (
        <EmptyState
          icon={NavIcon.keys}
          title="No API keys yet"
          message={
            isAdmin
              ? 'Create a key below to authenticate programmatic access to the API.'
              : 'An organization admin can create API keys for programmatic access.'
          }
        />
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table aria-label="API keys">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Prefix</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Last used</TableCell>
                {isAdmin && <TableCell align="right">Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {keys.map((key) => (
                <TableRow key={key.id} hover>
                  <TableCell>{key.name}</TableCell>
                  <TableCell>{key.prefix}&hellip;</TableCell>
                  <TableCell>{new Date(key.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'never'}
                  </TableCell>
                  {isAdmin && (
                    <TableCell align="right">
                      <Button
                        size="small"
                        color="error"
                        onClick={() => handleRevoke(key.id)}
                        startIcon={<DeleteActionIcon />}
                      >
                        Revoke
                      </Button>
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
            Create a new key
          </Typography>
          <Box
            component="form"
            onSubmit={handleCreate}
            sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 2, alignItems: { sm: 'center' } }}
          >
            <TextField
              size="small"
              label="Key name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              sx={{ flexGrow: 1 }}
            />
            <Button type="submit" variant="contained" startIcon={<AddActionIcon />}>
              Create key
            </Button>
          </Box>
        </Paper>
      )}

      <Dialog open={plaintext !== null} onClose={() => setPlaintext(null)}>
        <DialogTitle>Copy your API key now</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            This is the only time the full key is shown. Store it somewhere safe.
          </DialogContentText>
          <TextField value={plaintext ?? ''} fullWidth slotProps={{ input: { readOnly: true } }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPlaintext(null)}>Done</Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}
