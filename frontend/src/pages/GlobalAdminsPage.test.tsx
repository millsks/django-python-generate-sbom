import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GlobalAdminsPage } from './GlobalAdminsPage'
import { grantGlobalAdmin, listGlobalAdmins, revokeGlobalAdmin } from '../api/orgs'
import { ApiError } from '../api/client'

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return { ...actual, listGlobalAdmins: vi.fn(), grantGlobalAdmin: vi.fn(), revokeGlobalAdmin: vi.fn() }
})
const mockList = listGlobalAdmins as Mock
const mockGrant = grantGlobalAdmin as Mock
const mockRevoke = revokeGlobalAdmin as Mock

const ADMINS = [
  { user_id: 1, email: 'root@example.com' },
  { user_id: 2, email: 'bob@example.com' },
]

beforeEach(() => {
  mockList.mockReset()
  mockGrant.mockReset()
  mockRevoke.mockReset()
  mockList.mockResolvedValue({ global_admins: ADMINS })
})

describe('GlobalAdminsPage', () => {
  it('lists the current global admins', async () => {
    render(<GlobalAdminsPage />)
    expect(await screen.findByText('root@example.com')).toBeInTheDocument()
    expect(screen.getByText('bob@example.com')).toBeInTheDocument()
  })

  it('grants global admin by email and reloads', async () => {
    mockGrant.mockResolvedValue({ user_id: 3, email: 'carol@example.com' })
    const user = userEvent.setup()
    render(<GlobalAdminsPage />)
    await screen.findByText('root@example.com')

    await user.type(screen.getByLabelText(/email/i), 'carol@example.com')
    await user.click(screen.getByRole('button', { name: /grant/i }))

    await waitFor(() => expect(mockGrant).toHaveBeenCalledWith('carol@example.com'))
    await waitFor(() => expect(mockList).toHaveBeenCalledTimes(2)) // initial + reload
  })

  it('shows a no-such-user error when granting an unregistered email', async () => {
    mockGrant.mockRejectedValue(new ApiError('nope', 400, 'no_such_user'))
    const user = userEvent.setup()
    render(<GlobalAdminsPage />)
    await screen.findByText('root@example.com')

    await user.type(screen.getByLabelText(/email/i), 'ghost@example.com')
    await user.click(screen.getByRole('button', { name: /grant/i }))

    expect(await screen.findByText(/no registered user with that email/i)).toBeInTheDocument()
  })

  it('revokes a global admin after confirming in the dialog', async () => {
    mockRevoke.mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(<GlobalAdminsPage />)
    await screen.findByText('bob@example.com')

    // The 2nd row Revoke button targets bob (user_id 2); confirm in the dialog.
    await user.click(screen.getAllByRole('button', { name: /revoke/i })[1])
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /revoke/i }))

    await waitFor(() => expect(mockRevoke).toHaveBeenCalledWith(2))
  })

  it('shows a last-global-admin error when revoke is blocked', async () => {
    mockRevoke.mockRejectedValue(new ApiError('nope', 400, 'last_global_admin'))
    const user = userEvent.setup()
    render(<GlobalAdminsPage />)
    await screen.findByText('root@example.com')

    await user.click(screen.getAllByRole('button', { name: /revoke/i })[0])
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /revoke/i }))

    expect(await screen.findByText(/at least one global admin/i)).toBeInTheDocument()
  })

  it('cancels revoke without calling the API', async () => {
    const user = userEvent.setup()
    render(<GlobalAdminsPage />)
    await screen.findByText('bob@example.com')

    await user.click(screen.getAllByRole('button', { name: /revoke/i })[1])
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /cancel/i }))

    expect(mockRevoke).not.toHaveBeenCalled()
  })

  it('shows an error when the list fails to load', async () => {
    mockList.mockRejectedValue(new Error('boom'))
    render(<GlobalAdminsPage />)
    expect(await screen.findByText(/failed to load global admins/i)).toBeInTheDocument()
  })
})
