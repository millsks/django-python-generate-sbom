import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
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
      <RegisterPage />
    </MemoryRouter>,
  )
}

async function submit(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/email/i), 'newuser@example.com')
  await user.type(screen.getByLabelText(/password/i), 'pw12345678')
  await user.click(screen.getByRole('button', { name: /register/i }))
}

describe('RegisterPage', () => {
  it('shows a success message on a zero-org registration (org: null) without crashing', async () => {
    // Story 2.6: registration creates no org, so the response org is null.
    mockRegister.mockResolvedValue({ user: { id: 1, email: 'newuser@example.com' }, org: null })
    const user = userEvent.setup()
    renderPage()

    await submit(user)

    expect(await screen.findByText(/account created/i)).toBeInTheDocument()
    expect(screen.queryByText(/personal org/i)).not.toBeInTheDocument()
  })

  it('shows an error when registration fails', async () => {
    mockRegister.mockRejectedValue(new Error('boom'))
    const user = userEvent.setup()
    renderPage()

    await submit(user)

    expect(await screen.findByText(/registration failed/i)).toBeInTheDocument()
  })
})
