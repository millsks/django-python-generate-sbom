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
vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return { ...actual, getMembers: vi.fn().mockResolvedValue({ members: [], is_admin: false }) }
})
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock

describe('KeysPage', () => {
  it('shows the no-org state when there is no active org', async () => {
    mockAuth.mockReturnValue({ status: 'authed', activeOrg: null, isAdmin: false, refresh: vi.fn(), logout: vi.fn() })
    render(<KeysPage />)
    expect(await screen.findByText(NO_ORG_MESSAGE)).toBeInTheDocument()
  })
})
