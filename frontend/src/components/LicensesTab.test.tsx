import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LicensesTab } from './LicensesTab'
import { ApiError } from '../api/client'
import { getLicenses } from '../api/reports'
import { downloadWorkbook } from '../excelExport'

vi.mock('../api/reports', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/reports')>()
  return { ...actual, getLicenses: vi.fn() }
})
const mockGet = getLicenses as Mock

vi.mock('../excelExport', () => ({ buildWorkbook: vi.fn(() => ({})), downloadWorkbook: vi.fn() }))
const mockDownload = downloadWorkbook as Mock

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

  it('opens every accordion when Expand all is clicked', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<LicensesTab taskId="t" />)

    const weak = await screen.findByRole('button', { name: /Weak Copyleft/ })
    expect(weak).toHaveAttribute('aria-expanded', 'false')

    await userEvent.click(screen.getByRole('button', { name: /expand all/i }))

    for (const tier of ['Strong Copyleft', 'Weak Copyleft', 'Unknown', 'Permissive']) {
      expect(screen.getByRole('button', { name: new RegExp(tier) })).toHaveAttribute('aria-expanded', 'true')
    }
  })

  it('closes every accordion when Collapse all is clicked', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<LicensesTab taskId="t" />)

    const strong = await screen.findByRole('button', { name: /Strong Copyleft/ })
    expect(strong).toHaveAttribute('aria-expanded', 'true')

    await userEvent.click(screen.getByRole('button', { name: /collapse all/i }))

    for (const tier of ['Strong Copyleft', 'Weak Copyleft', 'Unknown', 'Permissive']) {
      expect(screen.getByRole('button', { name: new RegExp(tier) })).toHaveAttribute('aria-expanded', 'false')
    }
  })

  it('toggles an individual accordion independently of the others', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<LicensesTab taskId="t" />)

    const strong = await screen.findByRole('button', { name: /Strong Copyleft/ })
    const weak = screen.getByRole('button', { name: /Weak Copyleft/ })
    expect(strong).toHaveAttribute('aria-expanded', 'true')
    expect(weak).toHaveAttribute('aria-expanded', 'false')

    // Collapsing the populated tier leaves the others untouched.
    await userEvent.click(strong)
    expect(strong).toHaveAttribute('aria-expanded', 'false')
    expect(weak).toHaveAttribute('aria-expanded', 'false')

    // Expand-all still acts on every group afterwards.
    await userEvent.click(screen.getByRole('button', { name: /expand all/i }))
    expect(strong).toHaveAttribute('aria-expanded', 'true')
    expect(weak).toHaveAttribute('aria-expanded', 'true')
  })

  it('hides the expand/collapse controls when there are no tiers', async () => {
    mockGet.mockResolvedValue({ tiers: [], summary: {} })
    render(<LicensesTab taskId="t" />)

    // Wait for the report to load (the loading spinner disappears).
    await waitFor(() => expect(screen.queryByLabelText('Loading licenses')).not.toBeInTheDocument())
    expect(screen.queryByRole('button', { name: /expand all/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /collapse all/i })).not.toBeInTheDocument()
  })

  it('hides the expand/collapse controls when the report failed', async () => {
    mockGet.mockRejectedValue(new ApiError('failed', 404, 'report_failed', 'pypi down'))
    render(<LicensesTab taskId="t" />)

    await screen.findByText(/could not be generated/i)
    expect(screen.queryByRole('button', { name: /expand all/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /collapse all/i })).not.toBeInTheDocument()
  })

  it('exports the license report to an .xlsx on demand (Story 8.14)', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<LicensesTab taskId="t" />)

    await userEvent.click(await screen.findByRole('button', { name: 'Export to Excel' }))

    expect(mockDownload).toHaveBeenCalledWith(expect.anything(), 'licenses.xlsx')
  })

  it('hides the export control when there are no tiers', async () => {
    mockGet.mockResolvedValue({ tiers: [], summary: {} })
    render(<LicensesTab taskId="t" />)

    await waitFor(() => expect(screen.queryByLabelText('Loading licenses')).not.toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Export to Excel' })).not.toBeInTheDocument()
  })
})
