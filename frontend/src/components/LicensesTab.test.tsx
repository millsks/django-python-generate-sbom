import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LicensesTab } from './LicensesTab'
import { ApiError } from '../api/client'
import { getLicenses } from '../api/reports'

vi.mock('../api/reports', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/reports')>()
  return { ...actual, getLicenses: vi.fn() }
})
const mockGet = getLicenses as Mock

const REPORT = {
  tiers: [
    { tier: 'Strong Copyleft', packages: [{ name: 'agpl-pkg', version: '1.0', license: 'AGPL-3.0-only' }] },
    { tier: 'Weak Copyleft', packages: [] },
    { tier: 'Unknown', packages: [{ name: 'mystery', version: '2.0', license: 'UNKNOWN' }] },
    { tier: 'Permissive', packages: [{ name: 'mit-pkg', version: '3.0', license: 'MIT' }] },
  ],
  summary: { 'Strong Copyleft': 1, 'Weak Copyleft': 0, Unknown: 1, Permissive: 1 },
}

describe('LicensesTab', () => {
  it('renders the four tiers in descending-attention order', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<LicensesTab taskId="t" />)

    const headers = await screen.findAllByRole('button', { name: /Copyleft|Unknown|Permissive/ })
    const order = headers.map((h) => h.textContent)
    expect(order[0]).toMatch(/Strong Copyleft/)
    expect(order[1]).toMatch(/Weak Copyleft/)
    expect(order[2]).toMatch(/Unknown/)
    expect(order[3]).toMatch(/Permissive/)
  })

  it('collapses an empty tier and expands a populated one', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<LicensesTab taskId="t" />)

    const strong = await screen.findByRole('button', { name: /Strong Copyleft/ })
    const weak = screen.getByRole('button', { name: /Weak Copyleft/ })
    expect(strong).toHaveAttribute('aria-expanded', 'true') // populated
    expect(weak).toHaveAttribute('aria-expanded', 'false') // empty → collapsed
  })

  it('links package names to their PyPI page', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<LicensesTab taskId="t" />)

    const link = await screen.findByRole('link', { name: 'agpl-pkg' })
    expect(link).toHaveAttribute('href', 'https://pypi.org/project/agpl-pkg/')
  })

  it('renders the failure notice when the report failed', async () => {
    mockGet.mockRejectedValue(new ApiError('failed', 404, 'report_failed', 'pypi down'))
    render(<LicensesTab taskId="t" />)

    expect(await screen.findByText(/could not be generated/i)).toBeInTheDocument()
    expect(screen.getByText(/pypi down/i)).toBeInTheDocument()
  })
})
