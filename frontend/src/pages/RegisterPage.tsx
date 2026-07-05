import { useEffect, useState, type FormEvent } from 'react'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Link from '@mui/material/Link'
import Paper from '@mui/material/Paper'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { register } from '../api/auth'

// After a successful registration, send the user to login automatically so they don't
// have to hunt for a link (Story 10.3). Named so the UI copy and the test agree.
const REDIRECT_DELAY_MS = 5000

export function RegisterPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [registered, setRegistered] = useState(false)

  useEffect(() => {
    if (!registered) return
    const timer = setTimeout(() => navigate('/login'), REDIRECT_DELAY_MS)
    return () => clearTimeout(timer)
  }, [registered, navigate])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await register(email, password)
      setRegistered(true)
    } catch {
      setError('Registration failed. That email may already be in use.')
    }
  }

  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Create your account
      </Typography>
      {registered ? (
        <Alert severity="success">
          Registration successful — redirecting to login…{' '}
          <Link component={RouterLink} to="/login">
            Go to login now
          </Link>
        </Alert>
      ) : (
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
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button type="submit" variant="contained">
            Register
          </Button>
        </Paper>
      )}
    </Container>
  )
}
