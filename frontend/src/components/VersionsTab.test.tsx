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
    { name: 'alpha', installed: '1.0', latest: '1.1', currency: 'current', lts: null, on_lts: null },
    { name: 'bravo', installed: '2.0', latest: '5.0', currency: 'behind-2+', lts: null, on_lts: null },
    { name: 'charlie', installed: '3.0', latest: '3.1', currency: 'behind-1', lts: null, on_lts: null },
    { name: 'delta', installed: '4.0', latest: null, currency: 'unknown', lts: null, on_lts: null },
  ],
  summary: { current: 1, 'behind-1': 1, 'behind-2+': 1, unknown: 1 },
}

// Ground truth after Story 8.7's EOL fix: a package on its current LTS shows the
// green chip; Django 4.2.x (past its 2026-04-07 EOL) points at the current LTS 5.2.
const LTS_REPORT = {
  packages: [
    { name: 'wagtail', installed: '7.4.0', latest: '7.4.1', currency: 'current', lts: '7.4', on_lts: true },
    { name: 'django', installed: '4.2.30', latest: '5.2.0', currency: 'behind-2+', lts: '5.2', on_lts: false },
    { name: 'requests', installed: '2.0', latest: '2.1', currency: 'current', lts: null, on_lts: null },
  ],
  summary: { current: 2, 'behind-1': 0, 'behind-2+': 1, unknown: 0 },
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

  it('shows LTS status per package: on-LTS, off-LTS target, and untracked', async () => {
    mockGet.mockResolvedValue(LTS_REPORT)
    render(<VersionsTab taskId="t" />)

    const table = await screen.findByRole('table')
    const rowFor = (name: string) =>
      within(table)
        .getAllByRole('row')
        .find((r) => within(r).queryByText(name))!

    expect(within(rowFor('wagtail')).getByText('On LTS (7.4)')).toBeInTheDocument()
    expect(within(rowFor('django')).getByText('LTS 5.2 (target)')).toBeInTheDocument()
    // Untracked package shows a dash, not an LTS chip.
    expect(within(rowFor('requests')).queryByText(/LTS/)).not.toBeInTheDocument()
  })

  it('links package names to their registry and shows a source badge (Story 8.9)', async () => {
    mockGet.mockResolvedValue({
      packages: [
        { name: 'django', installed: '5.2.1', latest: '5.2.1', currency: 'current', lts: null, on_lts: null, ecosystem: 'pypi' },
        { name: 'numpy', installed: '1.26.0', latest: '1.26.4', currency: 'behind-1', lts: null, on_lts: null, ecosystem: 'conda' },
        { name: 'mystery', installed: '1.0', latest: '1.0', currency: 'current', lts: null, on_lts: null },
      ],
      summary: { current: 2, 'behind-1': 1, 'behind-2+': 0, unknown: 0 },
    })
    render(<VersionsTab taskId="t" />)

    const table = await screen.findByRole('table')
    expect(within(table).getByRole('link', { name: 'django' })).toHaveAttribute(
      'href',
      'https://pypi.org/project/django/5.2.1/',
    )
    expect(within(table).getByRole('link', { name: 'numpy' })).toHaveAttribute(
      'href',
      'https://prefix.dev/channels/conda-forge/packages/numpy',
    )
    // Unknown ecosystem → plain text, no link.
    expect(within(table).queryByRole('link', { name: 'mystery' })).not.toBeInTheDocument()
    expect(within(table).getByText('mystery')).toBeInTheDocument()
    // Source badges.
    expect(within(table).getByText('PyPI')).toBeInTheDocument()
    expect(within(table).getByText('Conda')).toBeInTheDocument()
  })

  it('renders the failure notice when the report failed', async () => {
    mockGet.mockRejectedValue(new ApiError('failed', 404, 'report_failed', 'pypi down'))
    render(<VersionsTab taskId="t" />)

    expect(await screen.findByText(/could not be generated/i)).toBeInTheDocument()
    expect(screen.getByText(/pypi down/i)).toBeInTheDocument()
  })
})
