import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MembersPage } from './MembersPage'
import { addMember, createMemberUser, getMembers, promoteAdmin } from '../api/orgs'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { NO_ORG_MESSAGE } from '../components/NoOrgState'

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return {
    ...actual,
    getMembers: vi.fn().mockResolvedValue({ members: [], is_admin: false }),
    addMember: vi.fn(),
    createMemberUser: vi.fn(),
    removeMember: vi.fn(),
    promoteAdmin: vi.fn(),
  }
})
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock
const mockGetMembers = getMembers as Mock
const mockAddMember = addMember as Mock
const mockCreateMemberUser = createMemberUser as Mock
const mockPromoteAdmin = promoteAdmin as Mock

beforeEach(() => {
  mockGetMembers.mockResolvedValue({ members: [], is_admin: false })
  mockAddMember.mockReset()
  mockCreateMemberUser.mockReset()
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

  it('creates a new user with a temp password (Story 2.10)', async () => {
    mockGetMembers.mockResolvedValue({ members: [], is_admin: true })
    mockCreateMemberUser.mockResolvedValue({ user_id: 3, email: 'newbie@example.com', role: 'member', joined_at: '' })
    const user = userEvent.setup()
    render(<MembersPage />)

    await user.click(await screen.findByRole('button', { name: /create new user/i }))
    await user.type(screen.getByLabelText(/email/i), 'newbie@example.com')
    await user.type(screen.getByLabelText(/temp password/i), 'temp12345')
    await user.click(screen.getByRole('button', { name: /create user/i }))

    await waitFor(() => expect(mockCreateMemberUser).toHaveBeenCalledWith('newbie@example.com', 'temp12345'))
    expect(mockAddMember).not.toHaveBeenCalled()
  })

  it('surfaces the email-taken error on the create path (Story 2.10)', async () => {
    mockGetMembers.mockResolvedValue({ members: [], is_admin: true })
    mockCreateMemberUser.mockRejectedValue(new ApiError('A user with that email already exists.', 400, 'email_taken'))
    const user = userEvent.setup()
    render(<MembersPage />)

    await user.click(await screen.findByRole('button', { name: /create new user/i }))
    await user.type(screen.getByLabelText(/email/i), 'bob@example.com')
    await user.type(screen.getByLabelText(/temp password/i), 'temp12345')
    await user.click(screen.getByRole('button', { name: /create user/i }))

    expect(await screen.findByText(/already exists/i)).toBeInTheDocument()
  })

  it('promotes a member to admin via "Make admin" (Story 2.16)', async () => {
    mockGetMembers.mockResolvedValue({
      members: [{ user_id: 2, email: 'bob@example.com', role: 'member', joined_at: '2026-01-01' }],
      is_admin: true,
    })
    mockPromoteAdmin.mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(<MembersPage />)

    await user.click(await screen.findByRole('button', { name: /make admin/i }))

    await waitFor(() => expect(mockPromoteAdmin).toHaveBeenCalledWith(2))
  })

  it('shows an error when "Make admin" fails', async () => {
    mockGetMembers.mockResolvedValue({
      members: [{ user_id: 2, email: 'bob@example.com', role: 'member', joined_at: '2026-01-01' }],
      is_admin: true,
    })
    mockPromoteAdmin.mockRejectedValue(new Error('boom'))
    const user = userEvent.setup()
    render(<MembersPage />)

    await user.click(await screen.findByRole('button', { name: /make admin/i }))

    expect(await screen.findByText(/could not make admin/i)).toBeInTheDocument()
  })
})
