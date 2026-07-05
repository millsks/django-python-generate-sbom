import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OrgSwitcher } from './OrgSwitcher'
import { getOrgs } from '../api/orgs'

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return { ...actual, getOrgs: vi.fn() }
})
const mockGetOrgs = getOrgs as Mock

describe('OrgSwitcher', () => {
  beforeEach(() => {
    mockGetOrgs.mockReset()
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
})
