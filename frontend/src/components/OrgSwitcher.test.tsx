import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OrgSwitcher } from './OrgSwitcher'
import { getOrgs, switchOrg } from '../api/orgs'

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return { ...actual, getOrgs: vi.fn(), switchOrg: vi.fn() }
})
const mockGetOrgs = getOrgs as Mock
const mockSwitchOrg = switchOrg as Mock
const reloadMock = vi.fn()

describe('OrgSwitcher', () => {
  beforeEach(() => {
    mockGetOrgs.mockReset()
    mockSwitchOrg.mockReset()
    reloadMock.mockReset()
    Object.defineProperty(window, 'location', {
      configurable: true,
      writable: true,
      value: { ...window.location, reload: reloadMock },
    })
  })

  it('shows a create-organization affordance when the user has zero orgs', async () => {
    mockGetOrgs.mockResolvedValue([])
    render(<OrgSwitcher />)

    const createButton = await screen.findByRole('button', { name: /create organization/i })
    // Opens the reusable create-org dialog.
    await userEvent.click(createButton)
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByLabelText(/organization name/i)).toBeInTheDocument()
  })

  it('renders the org select when the user has orgs', async () => {
    mockGetOrgs.mockResolvedValue([
      { slug: 'acme', name: 'Acme', active: true },
      { slug: 'globex', name: 'Globex', active: false },
    ])
    render(<OrgSwitcher />)

    expect(await screen.findByRole('combobox', { name: /org/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /create organization/i })).not.toBeInTheDocument()
  })

  it('opens the create-org dialog from the "New organization" item (Story 2.5)', async () => {
    mockGetOrgs.mockResolvedValue([{ slug: 'acme', name: 'Acme', active: true }])
    const user = userEvent.setup()
    render(<OrgSwitcher />)

    await user.click(await screen.findByRole('combobox', { name: /org/i }))
    await user.click(await screen.findByRole('option', { name: /new organization/i }))

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByLabelText(/organization name/i)).toBeInTheDocument()
  })

  it('switches org and reloads when a different org is chosen', async () => {
    mockGetOrgs.mockResolvedValue([
      { slug: 'acme', name: 'Acme', active: true },
      { slug: 'globex', name: 'Globex', active: false },
    ])
    mockSwitchOrg.mockResolvedValue({ slug: 'globex', name: 'Globex' })
    const user = userEvent.setup()
    render(<OrgSwitcher />)

    await user.click(await screen.findByRole('combobox', { name: /org/i }))
    await user.click(await screen.findByRole('option', { name: 'Globex' }))

    await waitFor(() => expect(mockSwitchOrg).toHaveBeenCalledWith('globex'))
    await waitFor(() => expect(reloadMock).toHaveBeenCalled())
  })
})
