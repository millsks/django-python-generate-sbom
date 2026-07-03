import { useEffect, useState, type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { getActiveOrg } from '../api/orgs'

type AuthState = 'checking' | 'authed' | 'anon'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>('checking')

  useEffect(() => {
    getActiveOrg()
      .then(() => setAuthState('authed'))
      .catch(() => setAuthState('anon'))
  }, [])

  if (authState === 'checking') {
    return null
  }
  if (authState === 'anon') {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}
