import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CreateOrgDialog } from './CreateOrgDialog'
import { createOrg, switchOrg } from '../api/orgs'

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return { ...actual, createOrg: vi.fn(), switchOrg: vi.fn() }
})
const mockCreateOrg = createOrg as Mock
const mockSwitchOrg = switchOrg as Mock
const reloadMock = vi.fn()

beforeEach(() => {
  mockCreateOrg.mockReset()
  mockSwitchOrg.mockReset()
  reloadMock.mockReset()
  Object.defineProperty(window, 'location', {
    configurable: true,
    writable: true,
    value: { ...window.location, reload: reloadMock },
  })
})

describe('CreateOrgDialog', () => {
  it('creates the org, switches into it, and reloads on success', async () => {
    mockCreateOrg.mockResolvedValue({ slug: 'acme', name: 'Acme' })
    mockSwitchOrg.mockResolvedValue({ slug: 'acme', name: 'Acme' })
    const user = userEvent.setup()
    render(<CreateOrgDialog open onClose={vi.fn()} />)

    await user.type(screen.getByLabelText(/organization name/i), 'Acme')
    await user.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() => expect(mockCreateOrg).toHaveBeenCalledWith('Acme'))
    expect(mockSwitchOrg).toHaveBeenCalledWith('acme')
    await waitFor(() => expect(reloadMock).toHaveBeenCalled())
  })

  it('surfaces an error and re-enables the form when creation fails', async () => {
    mockCreateOrg.mockRejectedValue(new Error('boom'))
    const user = userEvent.setup()
    render(<CreateOrgDialog open onClose={vi.fn()} />)

    await user.type(screen.getByLabelText(/organization name/i), 'Acme')
    await user.click(screen.getByRole('button', { name: /^create$/i }))

    expect(await screen.findByText(/could not create the organization/i)).toBeInTheDocument()
    expect(mockSwitchOrg).not.toHaveBeenCalled()
    expect(reloadMock).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /^create$/i })).toBeEnabled()
  })
})
