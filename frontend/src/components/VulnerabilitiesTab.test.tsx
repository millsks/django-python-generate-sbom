import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { VulnerabilitiesTab } from './VulnerabilitiesTab'
import { ApiError } from '../api/client'
import { getVulnerabilities } from '../api/reports'

vi.mock('../api/reports', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/reports')>()
  return { ...actual, getVulnerabilities: vi.fn() }
})
const mockGet = getVulnerabilities as Mock

function vuln(over: Record<string, unknown>) {
  return { id: 'GHSA', aliases: [], cve: null, cvss_score: null, severity: 'Low', advisory_url: 'http://a', cwe: [], ...over }
}

const REPORT = {
  packages: [
    { name: 'alpha', version: '1.0', vulnerabilities: [vuln({ id: 'GHSA-a', severity: 'Medium', cvss_score: 5 })] },
    { name: 'bravo', version: '2.0', vulnerabilities: [vuln({ id: 'GHSA-b', severity: 'Critical', cvss_score: 9.8 })] },
    { name: 'charlie', version: '3.0', vulnerabilities: [vuln({ id: 'GHSA-c', severity: 'Low', cvss_score: 3 })] },
  ],
  summary: { vulnerable_package_count: 3, severity_breakdown: { Critical: 1, Medium: 1, Low: 1 } },
}

async function dataRows() {
  const table = await screen.findByRole('table')
  const [, ...rows] = within(table).getAllByRole('row') // drop header
  return rows
}

describe('VulnerabilitiesTab', () => {
  it('sorts by severity rank (Critical first) by default', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<VulnerabilitiesTab taskId="t" totalPackages={10} />)

    const rows = await dataRows()
    expect(within(rows[0]).getByText('bravo')).toBeInTheDocument() // Critical
    expect(within(rows[2]).getByText('charlie')).toBeInTheDocument() // Low last
  })

  it('filters rows by severity', async () => {
    mockGet.mockResolvedValue(REPORT)
    render(<VulnerabilitiesTab taskId="t" totalPackages={10} />)
    await screen.findByRole('table')

    await userEvent.click(screen.getByRole('combobox', { name: /severity/i }))
    await userEvent.click(screen.getByRole('option', { name: 'Critical' }))

    const rows = await dataRows()
    expect(rows).toHaveLength(1)
    expect(within(rows[0]).getByText('bravo')).toBeInTheDocument()
  })

  it('shows an explicit zero-state with the scanned count', async () => {
    mockGet.mockResolvedValue({ packages: [], summary: { vulnerable_package_count: 0, severity_breakdown: {} } })
    render(<VulnerabilitiesTab taskId="t" totalPackages={42} />)

    expect(await screen.findByText('No vulnerabilities found in 42 packages.')).toBeInTheDocument()
  })

  it('renders the failure notice when the report failed', async () => {
    mockGet.mockRejectedValue(new ApiError('Report generation failed.', 404, 'report_failed', 'osv down'))
    render(<VulnerabilitiesTab taskId="t" totalPackages={10} />)

    expect(await screen.findByText(/could not be generated/i)).toBeInTheDocument()
    expect(screen.getByText(/osv down/i)).toBeInTheDocument()
  })
})
