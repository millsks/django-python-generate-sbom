import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AdminRoute } from './AdminRoute'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock
const authState = (over: Record<string, unknown>) => ({ status: 'authed', isAdmin: false, ...over })

function renderAt(initial = '/members') {
  render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route
          path="/members"
          element={
            <AdminRoute>
              <div>members page</div>
            </AdminRoute>
          }
        />
        <Route path="/" element={<div>home page</div>} />
        <Route path="/login" element={<div>login page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminRoute', () => {
  it('renders children for an admin', () => {
    mockAuth.mockReturnValue(authState({ isAdmin: true }))
    renderAt()
    expect(screen.getByText('members page')).toBeInTheDocument()
  })

  it('redirects an authenticated non-admin to the home page', () => {
    mockAuth.mockReturnValue(authState({ isAdmin: false }))
    renderAt()
    expect(screen.getByText('home page')).toBeInTheDocument()
    expect(screen.queryByText('members page')).not.toBeInTheDocument()
  })

  it('redirects an anonymous user to /login', () => {
    mockAuth.mockReturnValue(authState({ status: 'anon' }))
    renderAt()
    expect(screen.getByText('login page')).toBeInTheDocument()
  })

  it('renders nothing while auth is loading', () => {
    mockAuth.mockReturnValue(authState({ status: 'loading' }))
    renderAt()
    expect(screen.queryByText('members page')).not.toBeInTheDocument()
    expect(screen.queryByText('home page')).not.toBeInTheDocument()
    expect(screen.queryByText('login page')).not.toBeInTheDocument()
  })
})
