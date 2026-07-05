import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MembersPage } from './MembersPage'
import { useAuth } from '../auth/AuthProvider'
import { NO_ORG_MESSAGE } from '../components/NoOrgState'

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return {
    ...actual,
    getMembers: vi.fn().mockResolvedValue({ members: [], is_admin: false }),
    addMember: vi.fn(),
    removeMember: vi.fn(),
    transferAdmin: vi.fn(),
  }
})
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock

describe('MembersPage', () => {
  it('shows the no-org state when there is no active org', async () => {
    mockAuth.mockReturnValue({ status: 'authed', activeOrg: null, isAdmin: false, refresh: vi.fn(), logout: vi.fn() })
    render(<MembersPage />)
    expect(await screen.findByText(NO_ORG_MESSAGE)).toBeInTheDocument()
  })
})
