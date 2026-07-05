import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KeysPage } from './KeysPage'
import { useAuth } from '../auth/AuthProvider'
import { NO_ORG_MESSAGE } from '../components/NoOrgState'

vi.mock('../api/keys', () => ({
  getKeys: vi.fn().mockResolvedValue([]),
  createKey: vi.fn(),
  revokeKey: vi.fn(),
}))
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock
const authState = (over: Record<string, unknown>) => ({
  status: 'authed',
  activeOrg: { slug: 'acme', name: 'Acme' },
  isAdmin: false,
  refresh: vi.fn(),
  logout: vi.fn(),
  ...over,
})

describe('KeysPage', () => {
  it('shows the no-org state when there is no active org', async () => {
    mockAuth.mockReturnValue(authState({ activeOrg: null }))
    render(<KeysPage />)
    expect(await screen.findByText(NO_ORG_MESSAGE)).toBeInTheDocument()
  })

  it('shows the create-key form only for an admin (isAdmin from useAuth)', async () => {
    mockAuth.mockReturnValue(authState({ isAdmin: true }))
    render(<KeysPage />)
    expect(await screen.findByRole('button', { name: /create key/i })).toBeInTheDocument()
  })

  it('hides the create-key form for a non-admin member', async () => {
    mockAuth.mockReturnValue(authState({ isAdmin: false }))
    render(<KeysPage />)
    // Wait for load to settle, then assert the admin-only control is absent.
    await screen.findByRole('heading', { name: /api keys/i })
    expect(screen.queryByRole('button', { name: /create key/i })).not.toBeInTheDocument()
  })
})
