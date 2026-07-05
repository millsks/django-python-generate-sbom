import { useEffect, useState, type FormEvent } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { createKey, getKeys, revokeKey, type ApiKey } from '../api/keys'
import { getMembers } from '../api/orgs'
import { AddActionIcon, DeleteActionIcon } from '../icons'

export function KeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [isAdmin, setIsAdmin] = useState(false)
  const [name, setName] = useState('')
  const [plaintext, setPlaintext] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  function load() {
    getKeys()
      .then(setKeys)
      .catch(() => setError('Failed to load API keys.'))
    getMembers()
      .then((response) => setIsAdmin(response.is_admin))
      .catch(() => {})
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

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        API keys
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Prefix</TableCell>
            <TableCell>Created</TableCell>
            <TableCell>Last used</TableCell>
            {isAdmin && <TableCell>Actions</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {keys.map((key) => (
            <TableRow key={key.id}>
              <TableCell>{key.name}</TableCell>
              <TableCell>{key.prefix}&hellip;</TableCell>
              <TableCell>{new Date(key.created_at).toLocaleDateString()}</TableCell>
              <TableCell>
                {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'never'}
              </TableCell>
              {isAdmin && (
                <TableCell>
                  <Button size="small" color="error" onClick={() => handleRevoke(key.id)} startIcon={<DeleteActionIcon />}>
                    Revoke
                  </Button>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {isAdmin && (
        <Box
          component="form"
          onSubmit={handleCreate}
          sx={{ display: 'flex', gap: 2, mt: 3, alignItems: 'center' }}
        >
          <TextField
            size="small"
            label="Key name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <Button type="submit" variant="contained" startIcon={<AddActionIcon />}>
            Create key
          </Button>
        </Box>
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
