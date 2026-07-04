import { type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'

// Gate a route on authentication using the shared auth state (Story 10.1). While
// the initial check is in flight, render nothing; anonymous users go to /login
// (the return-to redirect is Story 10.2).
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()

  if (status === 'loading') {
    return null
  }
  if (status === 'anon') {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}
