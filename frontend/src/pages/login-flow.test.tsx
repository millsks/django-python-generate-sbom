// Integration regression test for the login bounce-loop (Story 10.2). Uses the REAL
// AuthProvider + ProtectedRoute + LoginPage and mocks only the API, so it exercises
// the exact symptom: after a successful login the user must land on the protected
// target and NOT be bounced back to the login form (which happens if the login flow
// navigates before refreshing the shared auth state).
import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthProvider'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { LoginPage } from './LoginPage'
import { getActiveOrg, getMembers } from '../api/orgs'
import { login } from '../api/auth'

vi.mock('../api/orgs', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/orgs')>()),
  getActiveOrg: vi.fn(),
  getMembers: vi.fn(),
}))
vi.mock('../api/auth', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/auth')>()),
  login: vi.fn(),
}))
const mockActiveOrg = getActiveOrg as Mock
const mockMembers = getMembers as Mock
const mockLogin = login as Mock

function renderApp(initial: string) {
  render(
    <AuthProvider>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route
            path="/upload"
            element={
              <ProtectedRoute>
                <div>upload page</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  )
}

async function submitLogin() {
  await userEvent.type(screen.getByLabelText(/email/i), 'a@b.com')
  await userEvent.type(screen.getByLabelText(/password/i), 'pw12345678')
  await userEvent.click(screen.getByRole('button', { name: /log in/i }))
}

describe('login flow (bounce-loop regression, Story 10.2)', () => {
  it('lands on the protected target after login and is NOT bounced back to /login', async () => {
    // Anonymous at mount (protected route bounces to /login), then authed after the
    // successful login triggers refresh() — so the target route stays rendered.
    mockActiveOrg.mockRejectedValueOnce(new Error('anon')).mockResolvedValue({ slug: 'acme', name: 'Acme' })
    mockMembers.mockResolvedValue({ is_admin: false, members: [] })
    mockLogin.mockResolvedValue({ org: { slug: 'acme', name: 'Acme' } })

    renderApp('/upload')

    // Bounced to the login form first (protected route, still anonymous).
    await screen.findByRole('button', { name: /log in/i })
    expect(screen.queryByText('upload page')).not.toBeInTheDocument()

    await submitLogin()

    // After login refreshes the auth state, we return to /upload — no bounce back.
    expect(await screen.findByText('upload page')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /log in/i })).not.toBeInTheDocument()
  })
})
