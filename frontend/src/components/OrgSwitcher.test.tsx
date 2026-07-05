import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OrgSwitcher } from './OrgSwitcher'
import { getOrgs, switchOrg } from '../api/orgs'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return { ...actual, getOrgs: vi.fn(), switchOrg: vi.fn() }
})
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockGetOrgs = getOrgs as Mock
const mockSwitchOrg = switchOrg as Mock
const mockAuth = useAuth as Mock
const reloadMock = vi.fn()

function setGlobalAdmin(isGlobalAdmin: boolean) {
  mockAuth.mockReturnValue({ status: 'authed', user: null, activeOrg: null, isAdmin: false, isGlobalAdmin, refresh: vi.fn(), logout: vi.fn() })
}

describe('OrgSwitcher', () => {
  beforeEach(() => {
    mockGetOrgs.mockReset()
    mockSwitchOrg.mockReset()
    reloadMock.mockReset()
    setGlobalAdmin(true) // default: global admin (create affordances visible)
    Object.defineProperty(window, 'location', {
      configurable: true,
      writable: true,
      value: { ...window.location, reload: reloadMock },
    })
  })

  it('shows a create-organization affordance to a global admin with zero orgs', async () => {
    mockGetOrgs.mockResolvedValue([])
    render(<OrgSwitcher />)

    const createButton = await screen.findByRole('button', { name: /create organization/i })
    await userEvent.click(createButton)
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByLabelText(/organization name/i)).toBeInTheDocument()
  })

  it('renders nothing for a non-global-admin with zero orgs (Story 2.12)', async () => {
    setGlobalAdmin(false)
    mockGetOrgs.mockResolvedValue([])
    const { container } = render(<OrgSwitcher />)
    await waitFor(() => expect(mockGetOrgs).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
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

  it('offers "New organization" to a global admin but not a regular member (Story 2.12)', async () => {
    mockGetOrgs.mockResolvedValue([{ slug: 'acme', name: 'Acme', active: true }])
    const user = userEvent.setup()

    // Global admin: the item is present.
    const { unmount } = render(<OrgSwitcher />)
    await user.click(await screen.findByRole('combobox', { name: /org/i }))
    expect(await screen.findByRole('option', { name: /new organization/i })).toBeInTheDocument()
    unmount()

    // Regular member: no "New organization" item.
    setGlobalAdmin(false)
    render(<OrgSwitcher />)
    await user.click(await screen.findByRole('combobox', { name: /org/i }))
    expect(screen.queryByRole('option', { name: /new organization/i })).not.toBeInTheDocument()
  })

  it('switches org and reloads when a different org is chosen', async () => {
    setGlobalAdmin(false)
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
