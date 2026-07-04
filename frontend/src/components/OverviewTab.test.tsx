import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OverviewTab } from './OverviewTab'
import type { JobStatus } from '../api/jobs'

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
})
