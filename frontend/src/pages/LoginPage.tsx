import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate, type Location } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Paper from '@mui/material/Paper'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { login } from '../api/auth'
import { useAuth } from '../auth/AuthProvider'

// Where to land after login when there's no intended destination.
const DEFAULT_AFTER_LOGIN = '/dashboard'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { status, refresh } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Where a ProtectedRoute sent us from (Story 10.2); a full Location preserves query/hash.
  const from = (location.state as { from?: Location } | null)?.from
  const target = from ?? DEFAULT_AFTER_LOGIN

  // Already signed in → don't show the form again; go to the intended page or the default.
  if (status === 'authed') {
    return <Navigate to={target} replace />
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await login(email, password)
      await refresh() // update the shared auth state so the nav/guards reflect the session
      navigate(target, { replace: true })
    } catch {
      setError('Invalid email or password.')
    }
  }

  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Log in
      </Typography>
      <Paper
        component="form"
        variant="outlined"
        onSubmit={handleSubmit}
        sx={{ display: 'flex', flexDirection: 'column', gap: 2, p: 3 }}
      >
        {error && <Alert severity="error">{error}</Alert>}
        <TextField
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          // Focus on arrival so a user redirected here from registration (Story 10.3) can
          // type immediately. The status==='authed' guard above means this form only renders
          // for anonymous visitors, so it never steals focus from a signed-in redirect.
          autoFocus
        />
        <TextField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <Button type="submit" variant="contained">
          Log in
        </Button>
      </Paper>
    </Container>
  )
}
