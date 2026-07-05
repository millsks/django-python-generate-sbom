import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MembersPage } from './MembersPage'
import { addMember, getMembers } from '../api/orgs'
import { ApiError } from '../api/client'
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
const mockGetMembers = getMembers as Mock
const mockAddMember = addMember as Mock

beforeEach(() => {
  mockGetMembers.mockResolvedValue({ members: [], is_admin: false })
  mockAddMember.mockReset()
  mockAuth.mockReturnValue({ status: 'authed', activeOrg: { slug: 'acme', name: 'Acme' }, isAdmin: true, refresh: vi.fn(), logout: vi.fn() })
})

describe('MembersPage', () => {
  it('shows the no-org state when there is no active org', async () => {
    mockAuth.mockReturnValue({ status: 'authed', activeOrg: null, isAdmin: false, refresh: vi.fn(), logout: vi.fn() })
    render(<MembersPage />)
    expect(await screen.findByText(NO_ORG_MESSAGE)).toBeInTheDocument()
  })

  it('adds an existing user by email (no password field)', async () => {
    mockGetMembers.mockResolvedValue({ members: [], is_admin: true })
    mockAddMember.mockResolvedValue({ user_id: 2, email: 'bob@example.com', role: 'member', joined_at: '' })
    const user = userEvent.setup()
    render(<MembersPage />)

    const emailField = await screen.findByLabelText(/email/i)
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument()
    await user.type(emailField, 'bob@example.com')
    await user.click(screen.getByRole('button', { name: /add member/i }))

    await waitFor(() => expect(mockAddMember).toHaveBeenCalledWith('bob@example.com'))
  })

  it('surfaces the no-such-user error distinctly', async () => {
    mockGetMembers.mockResolvedValue({ members: [], is_admin: true })
    mockAddMember.mockRejectedValue(new ApiError('No registered user with that email.', 400, 'no_such_user'))
    const user = userEvent.setup()
    render(<MembersPage />)

    await user.type(await screen.findByLabelText(/email/i), 'ghost@example.com')
    await user.click(screen.getByRole('button', { name: /add member/i }))

    expect(await screen.findByText(/no registered user with that email/i)).toBeInTheDocument()
  })

  it('surfaces the already-member error distinctly', async () => {
    mockGetMembers.mockResolvedValue({ members: [], is_admin: true })
    mockAddMember.mockRejectedValue(new ApiError('That user is already a member of this org.', 400, 'already_member'))
    const user = userEvent.setup()
    render(<MembersPage />)

    await user.type(await screen.findByLabelText(/email/i), 'bob@example.com')
    await user.click(screen.getByRole('button', { name: /add member/i }))

    expect(await screen.findByText(/already a member of this org/i)).toBeInTheDocument()
  })

  it('shows a generic error for an unexpected add failure', async () => {
    mockGetMembers.mockResolvedValue({ members: [], is_admin: true })
    mockAddMember.mockRejectedValue(new Error('boom'))
    const user = userEvent.setup()
    render(<MembersPage />)

    await user.type(await screen.findByLabelText(/email/i), 'bob@example.com')
    await user.click(screen.getByRole('button', { name: /add member/i }))

    expect(await screen.findByText(/could not add member/i)).toBeInTheDocument()
  })
})
