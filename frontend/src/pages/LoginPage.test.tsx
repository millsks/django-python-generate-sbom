import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { LoginPage } from './LoginPage'
import { login } from '../api/auth'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../api/auth', () => ({ login: vi.fn() }))
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockLogin = login as Mock
const mockUseAuth = useAuth as Mock

// No beforeEach mockReset on mockLogin: resetting a mock later given mockRejectedValue
// triggers a false vitest unhandled-rejection. Each test sets its own impl instead.
function renderLogin(state?: unknown) {
  render(
    <MemoryRouter initialEntries={[{ pathname: '/login', state }]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/upload" element={<div>upload page</div>} />
        <Route path="/" element={<div>index page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

async function submitLogin() {
  await userEvent.type(screen.getByLabelText(/email/i), 'a@b.com')
  await userEvent.type(screen.getByLabelText(/password/i), 'pw12345678')
  await userEvent.click(screen.getByRole('button', { name: /log in/i }))
}

describe('LoginPage', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({ status: 'anon', refresh: vi.fn().mockResolvedValue(undefined) })
  })

  it('autofocuses the email field on render (Story 10.4)', () => {
    renderLogin()

    expect(screen.getByLabelText(/email/i)).toHaveFocus()
  })

  it('returns to the intended page after a successful login (Story 10.2)', async () => {
    mockLogin.mockResolvedValue({ org: null })
    renderLogin({ from: { pathname: '/upload' } })

    await submitLogin()

    expect(await screen.findByText('upload page')).toBeInTheDocument()
  })

  it('falls back to the default when there is no intended destination', async () => {
    mockLogin.mockResolvedValue({ org: null })
    renderLogin()

    await submitLogin()

    expect(await screen.findByText('index page')).toBeInTheDocument()
  })

  it('redirects an already-authenticated user away from the form to the default', () => {
    mockUseAuth.mockReturnValue({ status: 'authed', refresh: vi.fn() })
    renderLogin()

    expect(screen.getByText('index page')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /log in/i })).not.toBeInTheDocument()
  })

  it('shows an error and stays on the form when login fails', async () => {
    mockLogin.mockRejectedValue(new Error('bad credentials'))
    renderLogin({ from: { pathname: '/upload' } })

    await submitLogin()

    expect(await screen.findByText(/invalid email or password/i)).toBeInTheDocument()
    expect(screen.queryByText('upload page')).not.toBeInTheDocument()
  })

  it('submits the form when Enter is pressed in a field (Story 10.6)', async () => {
    mockLogin.mockResolvedValue({ org: null })
    renderLogin()

    await userEvent.type(screen.getByLabelText(/email/i), 'a@b.com')
    // Enter in a text field should implicitly submit the form (there is a submit button).
    await userEvent.type(screen.getByLabelText(/password/i), 'pw12345678{Enter}')

    expect(mockLogin).toHaveBeenCalledWith('a@b.com', 'pw12345678')
    expect(await screen.findByText('index page')).toBeInTheDocument()
  })
})
