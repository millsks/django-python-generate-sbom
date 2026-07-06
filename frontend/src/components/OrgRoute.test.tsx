import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { OrgRoute } from './OrgRoute'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock
const authState = (over: Record<string, unknown>) => ({ status: 'authed', activeOrg: null, ...over })

function renderAt(initial = '/upload') {
  render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route
          path="/upload"
          element={
            <OrgRoute>
              <div>upload page</div>
            </OrgRoute>
          }
        />
        <Route path="/" element={<div>home page</div>} />
        <Route path="/login" element={<div>login page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('OrgRoute', () => {
  it('renders children for a user with an active org', () => {
    mockAuth.mockReturnValue(authState({ activeOrg: { slug: 'acme', name: 'Acme' } }))
    renderAt()
    expect(screen.getByText('upload page')).toBeInTheDocument()
  })

  it('redirects a zero-org user to the home page', () => {
    mockAuth.mockReturnValue(authState({ activeOrg: null }))
    renderAt()
    expect(screen.getByText('home page')).toBeInTheDocument()
    expect(screen.queryByText('upload page')).not.toBeInTheDocument()
  })

  it('redirects an anonymous user to /login', () => {
    mockAuth.mockReturnValue(authState({ status: 'anon' }))
    renderAt()
    expect(screen.getByText('login page')).toBeInTheDocument()
  })

  it('renders nothing while auth is loading', () => {
    mockAuth.mockReturnValue(authState({ status: 'loading' }))
    renderAt()
    expect(screen.queryByText('upload page')).not.toBeInTheDocument()
    expect(screen.queryByText('home page')).not.toBeInTheDocument()
    expect(screen.queryByText('login page')).not.toBeInTheDocument()
  })
})
