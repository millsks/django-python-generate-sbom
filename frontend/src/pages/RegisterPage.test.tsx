import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { RegisterPage } from './RegisterPage'
import { register } from '../api/auth'

vi.mock('../api/auth', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/auth')>()
  return { ...actual, register: vi.fn() }
})
const mockRegister = register as Mock

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/register']}>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<div>login-page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

// Synchronous form submit — used by the fake-timer tests, where userEvent's internal
// timer-driven waits would deadlock against vi.useFakeTimers().
async function submitSync() {
  fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'newuser@example.com' } })
  fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pw12345678' } })
  fireEvent.click(screen.getByRole('button', { name: /register/i }))
  // Flush the mocked register() resolution → setRegistered(true) → the redirect effect.
  await act(async () => {})
}

afterEach(() => {
  vi.useRealTimers()
})

describe('RegisterPage', () => {
  it('shows the redirect message and a manual login link on a zero-org success (org: null)', async () => {
    // Story 2.6: registration creates no org, so the response org is null.
    mockRegister.mockResolvedValue({ user: { id: 1, email: 'newuser@example.com' }, org: null })
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText(/email/i), 'newuser@example.com')
    await user.type(screen.getByLabelText(/password/i), 'pw12345678')
    await user.click(screen.getByRole('button', { name: /register/i }))

    expect(await screen.findByText(/registration successful/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /go to login now/i })).toBeInTheDocument()
    expect(screen.queryByText(/personal org/i)).not.toBeInTheDocument()
  })

  it('auto-redirects to /login after the delay', async () => {
    vi.useFakeTimers()
    mockRegister.mockResolvedValue({ user: { id: 1, email: 'newuser@example.com' }, org: null })
    renderPage()

    await submitSync()
    expect(screen.getByText(/registration successful/i)).toBeInTheDocument()
    expect(screen.queryByText('login-page')).not.toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(5000)
    })

    expect(screen.getByText('login-page')).toBeInTheDocument()
  })

  it('clears the redirect timer on unmount (no navigation after leaving)', async () => {
    vi.useFakeTimers()
    const clearSpy = vi.spyOn(globalThis, 'clearTimeout')
    mockRegister.mockResolvedValue({ user: { id: 1, email: 'newuser@example.com' }, org: null })
    const { unmount } = renderPage()

    await submitSync()
    expect(screen.getByText(/registration successful/i)).toBeInTheDocument()
    unmount()

    expect(clearSpy).toHaveBeenCalled()
    clearSpy.mockRestore()
  })

  it('shows an error when registration fails', async () => {
    mockRegister.mockRejectedValue(new Error('boom'))
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText(/email/i), 'newuser@example.com')
    await user.type(screen.getByLabelText(/password/i), 'pw12345678')
    await user.click(screen.getByRole('button', { name: /register/i }))

    expect(await screen.findByText(/registration failed/i)).toBeInTheDocument()
  })
})
