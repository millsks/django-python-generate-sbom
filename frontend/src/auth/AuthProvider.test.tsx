import { describe, expect, it, vi, beforeEach } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider, useAuth } from './AuthProvider'
import { getActiveOrg, getMembers } from '../api/orgs'
import { logout as apiLogout } from '../api/auth'

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return { ...actual, getActiveOrg: vi.fn(), getMembers: vi.fn() }
})
vi.mock('../api/auth', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/auth')>()
  return { ...actual, logout: vi.fn() }
})
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
    mockGetActiveOrg.mockReset()
    mockGetMembers.mockReset()
    mockLogout.mockReset()
  })

  it('resolves to authed with the org and admin flag', async () => {
    mockGetActiveOrg.mockResolvedValue({ slug: 'acme', name: 'Acme' })
    mockGetMembers.mockResolvedValue({ is_admin: true })
    renderProbe()

    expect(await screen.findByText('status:authed')).toBeInTheDocument()
    expect(screen.getByText('org:Acme')).toBeInTheDocument()
    expect(screen.getByText('admin:true')).toBeInTheDocument()
  })

  it('resolves to anon when the active-org call fails', async () => {
    mockGetActiveOrg.mockRejectedValue(new Error('401'))
    renderProbe()
    expect(await screen.findByText('status:anon')).toBeInTheDocument()
    expect(screen.getByText('admin:false')).toBeInTheDocument()
  })

  it('logout ends the session', async () => {
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
