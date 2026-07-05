import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'

// Gate a route on being an admin of the active org (Story 2.17). Loading → nothing;
// anonymous → /login (preserving the attempted location, like ProtectedRoute); an
// authenticated non-admin → redirected to the home page. This stops a non-admin from
// landing on an admin page by typing its URL; the API enforces the same rule server-side.
export function AdminRoute({ children }: { children: ReactNode }) {
  const { status, isAdmin } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return null
  }
  if (status === 'anon') {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  if (!isAdmin) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}
