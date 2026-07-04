import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './ProtectedRoute'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockUseAuth = useAuth as Mock

function renderProtected() {
  render(
    <MemoryRouter initialEntries={['/secret']}>
      <Routes>
        <Route
          path="/secret"
          element={
            <ProtectedRoute>
              <div>secret content</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div>login page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  it('renders the children when authenticated', () => {
    mockUseAuth.mockReturnValue({ status: 'authed' })
    renderProtected()
    expect(screen.getByText('secret content')).toBeInTheDocument()
  })

  it('redirects to /login when anonymous', () => {
    mockUseAuth.mockReturnValue({ status: 'anon' })
    renderProtected()
    expect(screen.getByText('login page')).toBeInTheDocument()
    expect(screen.queryByText('secret content')).not.toBeInTheDocument()
  })

  it('renders nothing while the auth check is loading', () => {
    mockUseAuth.mockReturnValue({ status: 'loading' })
    renderProtected()
    expect(screen.queryByText('secret content')).not.toBeInTheDocument()
    expect(screen.queryByText('login page')).not.toBeInTheDocument()
  })
})
