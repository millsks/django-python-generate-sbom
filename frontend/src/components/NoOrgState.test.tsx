import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NoOrgState, NO_ORG_MESSAGE } from './NoOrgState'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock

function authValue(isGlobalAdmin: boolean) {
  return { status: 'authed', user: null, activeOrg: null, isAdmin: false, isGlobalAdmin, refresh: vi.fn(), logout: vi.fn() }
}

describe('NoOrgState', () => {
  it('always shows the no-org message', () => {
    mockAuth.mockReturnValue(authValue(false))
    render(<NoOrgState />)
    expect(screen.getByText(NO_ORG_MESSAGE)).toBeInTheDocument()
  })

  it('hides the create-org affordance for a non-global-admin (Story 2.12)', () => {
    mockAuth.mockReturnValue(authValue(false))
    render(<NoOrgState />)
    expect(screen.queryByRole('button', { name: /create organization/i })).not.toBeInTheDocument()
  })

  it('shows and opens the create-org dialog for a global admin', async () => {
    mockAuth.mockReturnValue(authValue(true))
    const user = userEvent.setup()
    render(<NoOrgState />)

    await user.click(screen.getByRole('button', { name: /create organization/i }))

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByLabelText(/organization name/i)).toBeInTheDocument()
  })
})
