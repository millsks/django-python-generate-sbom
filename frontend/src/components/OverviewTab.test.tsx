import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OverviewTab } from './OverviewTab'
import type { JobStatus } from '../api/jobs'
import { getLicenses, getVersions, getVulnerabilities } from '../api/reports'
import { getSbomDocument } from '../api/sbom'
import { buildWorkbook, downloadWorkbook } from '../excelExport'

vi.mock('../api/reports', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/reports')>()
  return { ...actual, getVersions: vi.fn(), getVulnerabilities: vi.fn(), getLicenses: vi.fn() }
})
vi.mock('../api/sbom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/sbom')>()
  return { ...actual, getSbomDocument: vi.fn() }
})
vi.mock('../excelExport', () => ({ buildWorkbook: vi.fn(() => ({})), downloadWorkbook: vi.fn() }))

const mockVersions = getVersions as Mock
const mockVulns = getVulnerabilities as Mock
const mockLicenses = getLicenses as Mock
const mockSbom = getSbomDocument as Mock
const mockBuild = buildWorkbook as Mock
const mockDownload = downloadWorkbook as Mock
const sheetNames = () => (mockBuild.mock.calls.at(-1)![0] as { name: string }[]).map((s) => s.name)

function makeStatus(overrides: Partial<JobStatus> = {}): JobStatus {
  return {
    task_id: 'x',
    status: 'SUCCESS',
    progress: 100,
    current_phase: 'complete',
    failure_reason: null,
    result_url: '/api/v1/sbom/result/x/',
    output_format: 'cyclonedx-json',
    summary_stats: {
      total_packages: 42,
      reports: {
        vuln: { failed: false, failure_reason: null, vulnerable_package_count: 3 },
        license: {
          failed: false,
          failure_reason: null,
          'Strong Copyleft': 1,
          'Weak Copyleft': 2,
          Permissive: 30,
          Unknown: 9,
        },
        version: { failed: false, failure_reason: null, current: 20, 'behind-1': 10, 'behind-2+': 5, unknown: 7 },
      },
    },
    created_at: '',
    completed_at: null,
    artifacts_available: true,
    artifacts_expire_at: null,
    ...overrides,
  }
}

describe('OverviewTab', () => {
  it('renders the four metric groups from summary_stats', () => {
    render(<OverviewTab status={makeStatus()} onNavigate={vi.fn()} />)
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('3 vulnerable')).toBeInTheDocument()
    expect(screen.getByText('30 permissive · 3 copyleft · 9 unknown')).toBeInTheDocument()
    expect(screen.getByText('20 current · 15 behind · 7 unknown')).toBeInTheDocument()
  })

  it('has a SBOM download link reflecting the output format', () => {
    render(<OverviewTab status={makeStatus()} onNavigate={vi.fn()} />)
    const link = screen.getByRole('link', { name: /Download SBOM/ })
    expect(link).toHaveAttribute('href', '/api/v1/sbom/result/x/')
    expect(link).toHaveTextContent('cyclonedx-json')
  })

  it('shows "Unavailable" for a failed report rather than 0', () => {
    const status = makeStatus()
    status.summary_stats!.reports!.vuln = { failed: true, failure_reason: 'osv down' }
    render(<OverviewTab status={status} onNavigate={vi.fn()} />)
    expect(screen.getByText('Unavailable')).toBeInTheDocument()
    expect(screen.queryByText('3 vulnerable')).not.toBeInTheDocument()
  })

  it('deep-links a metric card to its detail tab', async () => {
    const onNavigate = vi.fn()
    render(<OverviewTab status={makeStatus()} onNavigate={onNavigate} />)
    await userEvent.click(screen.getByRole('button', { name: /Vulnerabilities/ }))
    expect(onNavigate).toHaveBeenCalledWith(2)
  })

  it('deep-links the Version currency card to its reordered tab index', async () => {
    const onNavigate = vi.fn()
    render(<OverviewTab status={makeStatus()} onNavigate={onNavigate} />)
    await userEvent.click(screen.getByRole('button', { name: /Version currency/ }))
    expect(onNavigate).toHaveBeenCalledWith(4)
  })

  it('exports all reports into one workbook, the SBOM sheet first (Stories 8.15/8.27)', async () => {
    mockSbom.mockResolvedValue({ format: 'cyclonedx-json', components: [], raw: '' })
    mockVersions.mockResolvedValue({ packages: [], summary: {} })
    mockVulns.mockResolvedValue({ packages: [], summary: { vulnerable_package_count: 0, severity_breakdown: {} } })
    mockLicenses.mockResolvedValue({ tiers: [], summary: {} })
    render(<OverviewTab status={makeStatus()} onNavigate={vi.fn()} />)

    await userEvent.click(screen.getByRole('button', { name: 'Export all to Excel' }))

    await waitFor(() => expect(mockDownload).toHaveBeenCalledWith(expect.anything(), 'sbom-report.xlsx'))
    expect(sheetNames()).toEqual(['SBOM Components', 'Version Currency', 'Vulnerabilities', 'Licenses'])
  })

  it('omits a failed report and still exports the rest (AC #3)', async () => {
    mockSbom.mockResolvedValue({ format: 'cyclonedx-json', components: [], raw: '' })
    mockVersions.mockResolvedValue({ packages: [], summary: {} })
    mockVulns.mockRejectedValue(new Error('vuln report failed'))
    mockLicenses.mockResolvedValue({ tiers: [], summary: {} })
    render(<OverviewTab status={makeStatus()} onNavigate={vi.fn()} />)

    await userEvent.click(screen.getByRole('button', { name: 'Export all to Excel' }))

    await waitFor(() => expect(mockDownload).toHaveBeenCalled())
    expect(sheetNames()).toEqual(['SBOM Components', 'Version Currency', 'Licenses'])
  })

  it('hides the export control when no report is available (AC #5)', () => {
    const status = makeStatus()
    status.summary_stats!.reports = {
      vuln: { failed: true, failure_reason: 'x' },
      license: { failed: true, failure_reason: 'x' },
      version: { failed: true, failure_reason: 'x' },
    }
    render(<OverviewTab status={status} onNavigate={vi.fn()} />)

    expect(screen.queryByRole('button', { name: 'Export all to Excel' })).not.toBeInTheDocument()
  })
})
