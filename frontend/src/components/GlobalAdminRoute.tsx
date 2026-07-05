import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'

// Gate a route on being a global admin (Story 13.1) — the platform-admin tier.
// Mirrors AdminRoute: loading → nothing; anonymous → /login (preserving the attempted
// location); an authenticated non-global-admin → redirected home. The API enforces the
// same rule server-side, so this is UX, not the security boundary.
export function GlobalAdminRoute({ children }: { children: ReactNode }) {
  const { status, isGlobalAdmin } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return null
  }
  if (status === 'anon') {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  if (!isGlobalAdmin) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}
