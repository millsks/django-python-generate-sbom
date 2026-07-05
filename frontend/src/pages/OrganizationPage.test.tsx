import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OrganizationPage } from './OrganizationPage'
import { useAuth } from '../auth/AuthProvider'
import { NO_ORG_MESSAGE } from '../components/NoOrgState'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock

function renderPage() {
  return render(
    <MemoryRouter>
      <OrganizationPage />
    </MemoryRouter>,
  )
}

describe('OrganizationPage', () => {
  it('renders the control center with links to members and API keys', () => {
    mockAuth.mockReturnValue({ status: 'authed', activeOrg: { slug: 'acme', name: 'Acme' }, isAdmin: true, refresh: vi.fn(), logout: vi.fn() })
    renderPage()

    expect(screen.getByRole('heading', { name: /^organization$/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /manage members/i })).toHaveAttribute('href', '/members')
    expect(screen.getByRole('link', { name: /manage api keys/i })).toHaveAttribute('href', '/keys')
  })

  it('shows the no-org state when there is no active org', () => {
    mockAuth.mockReturnValue({ status: 'authed', activeOrg: null, isAdmin: true, refresh: vi.fn(), logout: vi.fn() })
    renderPage()
    expect(screen.getByText(NO_ORG_MESSAGE)).toBeInTheDocument()
  })
})
