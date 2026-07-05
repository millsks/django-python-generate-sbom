// Shared auth state (Story 10.1): a single source of truth for whether the user is
// signed in, the active org, and whether they admin it — consumed by the nav shell
// and the route guards. Identity is decoupled from the active org (Story 2.6): auth
// is derived from the auth/me identity call, and admin flags (isAdmin / isGlobalAdmin)
// come from that SAME call (Story 2.17), so the client never probes an admin-only
// endpoint to learn its role. The active org is fetched separately (a user with zero
// orgs is still authed with activeOrg null).
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getMe, logout as apiLogout, type CurrentUser, type OrgSummary } from '../api/auth'
import { getActiveOrg } from '../api/orgs'

type Status = 'loading' | 'authed' | 'anon'

interface AuthValue {
  status: Status
  user: CurrentUser | null
  activeOrg: OrgSummary | null
  isAdmin: boolean
  isGlobalAdmin: boolean
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
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [activeOrg, setActiveOrg] = useState<OrgSummary | null>(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [isGlobalAdmin, setIsGlobalAdmin] = useState(false)

  const refresh = useCallback(async () => {
    // Identity first: only a failed auth/me call makes the user anonymous. The one
    // getMe() result feeds both the current user (Story 10.5) and global-admin (2.12).
    let me: CurrentUser
    try {
      me = await getMe()
    } catch {
      setUser(null)
      setIsGlobalAdmin(false)
      setActiveOrg(null)
      setIsAdmin(false)
      setStatus('anon')
      return
    }
    setUser(me)
    setIsGlobalAdmin(me.is_global_admin)
    setIsAdmin(me.is_admin) // admin of the active org, straight from auth/me (Story 2.17)
    // The active org is fetched separately — a rejected/404 here means the user simply
    // has no active org, NOT that they are signed out.
    try {
      setActiveOrg(await getActiveOrg())
    } catch {
      setActiveOrg(null)
    }
    setStatus('authed')
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } finally {
      setUser(null)
      setIsGlobalAdmin(false)
      setActiveOrg(null)
      setIsAdmin(false)
      setStatus('anon')
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const value = useMemo<AuthValue>(
    () => ({ status, user, activeOrg, isAdmin, isGlobalAdmin, refresh, logout }),
    [status, user, activeOrg, isAdmin, isGlobalAdmin, refresh, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
