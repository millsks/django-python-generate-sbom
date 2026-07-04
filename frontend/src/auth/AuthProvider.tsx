// Shared auth state (Story 10.1): a single source of truth for whether the user is
// signed in, the active org, and whether they admin it — consumed by both the nav
// shell and ProtectedRoute. There is no user/me endpoint; auth is derived from the
// active-org call, and admin status from the org membership call.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { logout as apiLogout, type OrgSummary } from '../api/auth'
import { getActiveOrg, getMembers } from '../api/orgs'

type Status = 'loading' | 'authed' | 'anon'

interface AuthValue {
  status: Status
  activeOrg: OrgSummary | null
  isAdmin: boolean
  refresh: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used within an AuthProvider')
  return value
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('loading')
  const [activeOrg, setActiveOrg] = useState<OrgSummary | null>(null)
  const [isAdmin, setIsAdmin] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const org = await getActiveOrg()
      setActiveOrg(org)
      setStatus('authed')
      try {
        const members = await getMembers()
        setIsAdmin(members.is_admin)
      } catch {
        setIsAdmin(false) // authed but membership lookup failed → treat as non-admin
      }
    } catch {
      setActiveOrg(null)
      setIsAdmin(false)
      setStatus('anon')
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } finally {
      setActiveOrg(null)
      setIsAdmin(false)
      setStatus('anon')
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const value = useMemo<AuthValue>(
    () => ({ status, activeOrg, isAdmin, refresh, logout }),
    [status, activeOrg, isAdmin, refresh, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
