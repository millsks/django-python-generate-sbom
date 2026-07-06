import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'

// Gate a route on having an active org (Story 2.18). Loading → nothing; anonymous →
// /login (preserving the attempted location, like ProtectedRoute); an authenticated
// user with no active org → redirected to the home page. This restricts a zero-org
// user (and a global admin, whose ADMIN org is never a working org) to home rather
// than letting them reach org-scoped pages that would only render an empty state.
export function OrgRoute({ children }: { children: ReactNode }) {
  const { status, activeOrg } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return null
  }
  if (status === 'anon') {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  if (!activeOrg) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}
