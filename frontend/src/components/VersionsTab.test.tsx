import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { VersionsTab } from './VersionsTab'
import { ApiError } from '../api/client'
import { getVersions } from '../api/reports'

vi.mock('../api/reports', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/reports')>()
  return { ...actual, getVersions: vi.fn() }
})
const mockGet = getVersions as Mock

const REPORT = {
  packages: [
    { name: 'alpha', installed: '1.0', latest: '1.1', currency: 'current', lts: null },
    { name: 'bravo', installed: '2.0', latest: '5.0', currency: 'behind-2+', lts: null },
    { name: 'charlie', installed: '3.0', latest: '3.1', currency: 'behind-1', lts: null },
    { name: 'delta', installed: '4.0', latest: null, currency: 'unknown', lts: null },
  ],
  summary: { current: 1, 'behind-1': 1, 'behind-2+': 1, unknown: 1 },
}

async function dataRows() {
  const table = await screen.findByRole('table')
  const [, ...rows] = within(table).getAllByRole('row')
  return rows
}

describe('VersionsTab', () => {
  it('orders the most-outdated (behind-2+) first by default', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<VersionsTab taskId="t" />)

    const rows = await dataRows()
    expect(within(rows[0]).getByText('bravo')).toBeInTheDocument() // behind-2+
    expect(within(rows[0]).getByText('Behind 2+')).toBeInTheDocument()
  })

  it('sorts by status when the Status header is clicked', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<VersionsTab taskId="t" />)
    await screen.findByRole('table')

    // Default is status/desc (behind-2+ first); clicking toggles to asc (unknown first).
    await userEvent.click(screen.getByRole('button', { name: 'Status' }))
    const rows = await dataRows()
    expect(within(rows[0]).getByText('delta')).toBeInTheDocument() // unknown, lowest rank
  })

  it('renders the failure notice when the report failed', async () => {
    mockGet.mockRejectedValue(new ApiError('failed', 404, 'report_failed', 'pypi down'))
    render(<VersionsTab taskId="t" />)

    expect(await screen.findByText(/could not be generated/i)).toBeInTheDocument()
    expect(screen.getByText(/pypi down/i)).toBeInTheDocument()
  })
})
