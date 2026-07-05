import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OrganizationPage } from './OrganizationPage'
import { useAuth } from '../auth/AuthProvider'
import { NO_ORG_MESSAGE } from '../components/NoOrgState'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock

function authValue(over: Record<string, unknown> = {}) {
  return {
    status: 'authed',
    user: { id: 1, email: 'me@example.com', is_admin: false, is_global_admin: false },
    activeOrg: { slug: 'acme', name: 'Acme' },
    isAdmin: true,
    isGlobalAdmin: false,
    refresh: vi.fn(),
    logout: vi.fn(),
    ...over,
  }
}

function renderPage() {
  return render(
    <MemoryRouter>
      <OrganizationPage />
    </MemoryRouter>,
  )
}

describe('OrganizationPage', () => {
  it('renders the control center with links to members and API keys', () => {
    mockAuth.mockReturnValue(authValue())
    renderPage()

    expect(screen.getByRole('heading', { name: /^organization$/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /manage members/i })).toHaveAttribute('href', '/members')
    expect(screen.getByRole('link', { name: /manage api keys/i })).toHaveAttribute('href', '/keys')
  })

  it('hides the create-org card for a non-global-admin (Story 2.12)', () => {
    mockAuth.mockReturnValue(authValue({ isGlobalAdmin: false }))
    renderPage()
    expect(screen.queryByRole('button', { name: /create organization/i })).not.toBeInTheDocument()
  })

  it('shows the create-org card for a global admin', () => {
    mockAuth.mockReturnValue(authValue({ isGlobalAdmin: true }))
    renderPage()
    expect(screen.getByRole('button', { name: /create organization/i })).toBeInTheDocument()
  })

  it('shows the no-org state when there is no active org', () => {
    mockAuth.mockReturnValue(authValue({ activeOrg: null }))
    renderPage()
    expect(screen.getByText(NO_ORG_MESSAGE)).toBeInTheDocument()
  })
})
