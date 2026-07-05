import { describe, expect, it, vi, beforeEach } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider, useAuth } from './AuthProvider'
import { getActiveOrg, getMembers } from '../api/orgs'
import { getMe, logout as apiLogout } from '../api/auth'

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return { ...actual, getActiveOrg: vi.fn(), getMembers: vi.fn() }
})
vi.mock('../api/auth', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/auth')>()
  return { ...actual, getMe: vi.fn(), logout: vi.fn() }
})
const mockGetMe = getMe as Mock
const mockGetActiveOrg = getActiveOrg as Mock
const mockGetMembers = getMembers as Mock
const mockLogout = apiLogout as Mock

function Probe() {
  const { status, activeOrg, isAdmin, logout } = useAuth()
  return (
    <div>
      <span>status:{status}</span>
      <span>org:{activeOrg?.name ?? '-'}</span>
      <span>admin:{String(isAdmin)}</span>
      <button onClick={() => void logout()}>do-logout</button>
    </div>
  )
}

const renderProbe = () =>
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  )

describe('AuthProvider', () => {
  beforeEach(() => {
    mockGetMe.mockReset()
    mockGetActiveOrg.mockReset()
    mockGetMembers.mockReset()
    mockLogout.mockReset()
  })

  it('resolves to authed with the org and admin flag', async () => {
    mockGetMe.mockResolvedValue({ id: 1, email: 'a@b.com' })
    mockGetActiveOrg.mockResolvedValue({ slug: 'acme', name: 'Acme' })
    mockGetMembers.mockResolvedValue({ is_admin: true })
    renderProbe()

    expect(await screen.findByText('status:authed')).toBeInTheDocument()
    expect(screen.getByText('org:Acme')).toBeInTheDocument()
    expect(screen.getByText('admin:true')).toBeInTheDocument()
  })

  it('resolves to anon when the identity (auth/me) call fails', async () => {
    mockGetMe.mockRejectedValue(new Error('403'))
    renderProbe()
    expect(await screen.findByText('status:anon')).toBeInTheDocument()
    expect(screen.getByText('admin:false')).toBeInTheDocument()
  })

  it('stays authed with a null org when getMe succeeds but the active-org call 404s', async () => {
    // A logged-in user with zero orgs: identity resolves, active-org rejects — the
    // user is authenticated with no active org, NOT bounced to anonymous.
    mockGetMe.mockResolvedValue({ id: 1, email: 'a@b.com' })
    mockGetActiveOrg.mockRejectedValue(new Error('404'))
    renderProbe()
    expect(await screen.findByText('status:authed')).toBeInTheDocument()
    expect(screen.getByText('org:-')).toBeInTheDocument()
    expect(screen.getByText('admin:false')).toBeInTheDocument()
    expect(mockGetMembers).not.toHaveBeenCalled()
  })

  it('logout ends the session', async () => {
    mockGetMe.mockResolvedValue({ id: 1, email: 'a@b.com' })
    mockGetActiveOrg.mockResolvedValue({ slug: 'acme', name: 'Acme' })
    mockGetMembers.mockResolvedValue({ is_admin: false })
    mockLogout.mockResolvedValue(undefined)
    renderProbe()
    await screen.findByText('status:authed')

    await userEvent.click(screen.getByRole('button', { name: 'do-logout' }))

    await waitFor(() => expect(screen.getByText('status:anon')).toBeInTheDocument())
    expect(mockLogout).toHaveBeenCalled()
  })
})
