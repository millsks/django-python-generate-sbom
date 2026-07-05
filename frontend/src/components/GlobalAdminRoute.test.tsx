import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { GlobalAdminRoute } from './GlobalAdminRoute'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock
const authState = (over: Record<string, unknown>) => ({ status: 'authed', isGlobalAdmin: false, ...over })

function renderAt(initial = '/platform/global-admins') {
  render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route
          path="/platform/global-admins"
          element={
            <GlobalAdminRoute>
              <div>global admins page</div>
            </GlobalAdminRoute>
          }
        />
        <Route path="/" element={<div>home page</div>} />
        <Route path="/login" element={<div>login page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('GlobalAdminRoute', () => {
  it('renders children for a global admin', () => {
    mockAuth.mockReturnValue(authState({ isGlobalAdmin: true }))
    renderAt()
    expect(screen.getByText('global admins page')).toBeInTheDocument()
  })

  it('redirects an authenticated non-global-admin to the home page', () => {
    mockAuth.mockReturnValue(authState({ isGlobalAdmin: false }))
    renderAt()
    expect(screen.getByText('home page')).toBeInTheDocument()
    expect(screen.queryByText('global admins page')).not.toBeInTheDocument()
  })

  it('redirects an anonymous user to /login', () => {
    mockAuth.mockReturnValue(authState({ status: 'anon' }))
    renderAt()
    expect(screen.getByText('login page')).toBeInTheDocument()
  })

  it('renders nothing while auth is loading', () => {
    mockAuth.mockReturnValue(authState({ status: 'loading' }))
    renderAt()
    expect(screen.queryByText('global admins page')).not.toBeInTheDocument()
    expect(screen.queryByText('home page')).not.toBeInTheDocument()
    expect(screen.queryByText('login page')).not.toBeInTheDocument()
  })
})
