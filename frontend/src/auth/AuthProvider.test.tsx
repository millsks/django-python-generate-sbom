import { describe, expect, it, vi, beforeEach } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider, useAuth } from './AuthProvider'
import { getActiveOrg } from '../api/orgs'
import { getAppConfig } from '../api/config'
import { getMe, logout as apiLogout, type CurrentUser } from '../api/auth'

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return { ...actual, getActiveOrg: vi.fn() }
})
vi.mock('../api/auth', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/auth')>()
  return { ...actual, getMe: vi.fn(), logout: vi.fn() }
})
vi.mock('../api/config', () => ({ getAppConfig: vi.fn() }))
const mockGetMe = getMe as Mock
const mockGetActiveOrg = getActiveOrg as Mock
const mockGetAppConfig = getAppConfig as Mock
const mockLogout = apiLogout as Mock

// auth/me now carries the admin flags (Story 2.17), so AuthProvider derives isAdmin
// from it directly — no separate members probe.
const me = (over: Partial<CurrentUser> = {}): CurrentUser => ({
  id: 1,
  email: 'a@b.com',
  is_admin: false,
  is_global_admin: false,
  ...over,
})

function Probe() {
  const { status, activeOrg, isAdmin, apiDocsEnabled, logout } = useAuth()
  return (
    <div>
      <span>status:{status}</span>
      <span>org:{activeOrg?.name ?? '-'}</span>
      <span>admin:{String(isAdmin)}</span>
      <span>apidocs:{String(apiDocsEnabled)}</span>
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
    mockLogout.mockReset()
    mockGetAppConfig.mockResolvedValue({ api_docs_enabled: false })
  })

  it('resolves to authed with the org and admin flag from auth/me', async () => {
    mockGetMe.mockResolvedValue(me({ is_admin: true }))
    mockGetActiveOrg.mockResolvedValue({ slug: 'acme', name: 'Acme' })
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
    mockGetMe.mockResolvedValue(me({ is_admin: false }))
    mockGetActiveOrg.mockRejectedValue(new Error('404'))
    renderProbe()
    expect(await screen.findByText('status:authed')).toBeInTheDocument()
    expect(screen.getByText('org:-')).toBeInTheDocument()
    expect(screen.getByText('admin:false')).toBeInTheDocument()
  })

  it('exposes apiDocsEnabled from the public config endpoint (Story 11.20)', async () => {
    mockGetMe.mockResolvedValue(me())
    mockGetActiveOrg.mockResolvedValue({ slug: 'acme', name: 'Acme' })
    mockGetAppConfig.mockResolvedValueOnce({ api_docs_enabled: true })
    renderProbe()
    expect(await screen.findByText('apidocs:true')).toBeInTheDocument()
  })

  it('defaults apiDocsEnabled to false when the config fetch fails', async () => {
    mockGetMe.mockResolvedValue(me())
    mockGetActiveOrg.mockResolvedValue({ slug: 'acme', name: 'Acme' })
    mockGetAppConfig.mockRejectedValueOnce(new Error('500'))
    renderProbe()
    expect(await screen.findByText('status:authed')).toBeInTheDocument()
    expect(screen.getByText('apidocs:false')).toBeInTheDocument()
  })

  it('logout ends the session', async () => {
    mockGetMe.mockResolvedValue(me())
    mockGetActiveOrg.mockResolvedValue({ slug: 'acme', name: 'Acme' })
    mockLogout.mockResolvedValue(undefined)
    renderProbe()
    await screen.findByText('status:authed')

    await userEvent.click(screen.getByRole('button', { name: 'do-logout' }))

    await waitFor(() => expect(screen.getByText('status:anon')).toBeInTheDocument())
    expect(mockLogout).toHaveBeenCalled()
  })
})
