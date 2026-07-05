import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DashboardPage } from './DashboardPage'
import { useAuth } from '../auth/AuthProvider'
import { NO_ORG_MESSAGE } from '../components/NoOrgState'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock

describe('DashboardPage', () => {
  it('shows the no-org state for an authenticated user with no active org', () => {
    mockAuth.mockReturnValue({ status: 'authed', activeOrg: null, isAdmin: false, refresh: vi.fn(), logout: vi.fn() })
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    expect(screen.getByText(NO_ORG_MESSAGE)).toBeInTheDocument()
  })
})
