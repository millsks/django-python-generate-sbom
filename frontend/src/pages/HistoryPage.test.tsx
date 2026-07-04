import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { HistoryPage } from './HistoryPage'
import { getJobStatus, listJobs } from '../api/jobs'

vi.mock('../api/jobs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/jobs')>()
  return { ...actual, listJobs: vi.fn(), getJobStatus: vi.fn() }
})
const mockList = listJobs as Mock
const mockJobStatus = getJobStatus as Mock

function jobStatus(overrides: Record<string, unknown> = {}) {
  return {
    task_id: 'abc-123',
    status: 'PROGRESS',
    progress: 62,
    current_phase: 'vulnerability scan',
    failure_reason: null,
    result_url: null,
    created_at: '',
    completed_at: null,
    ...overrides,
  }
}

function page(results: unknown[], count = results.length) {
  return { count, next: count > 25 ? '/api/v1/sbom/jobs/?page=2' : null, previous: null, results }
}

const JOB = {
  task_id: 'abc-123',
  created_at: '2026-01-02T03:04:05Z',
  manifest_filename: 'requirements.txt',
  manifest_format: 'requirements',
  output_format: 'cyclonedx-json',
  status: 'SUCCESS',
  failure_reason: null,
}

function renderPage() {
  render(
    <MemoryRouter>
      <HistoryPage />
    </MemoryRouter>,
  )
}

describe('HistoryPage', () => {
  it('renders a row with its columns and a results link', async () => {
    mockList.mockResolvedValue(page([JOB]))
    renderPage()

    const table = await screen.findByRole('table')
    const rows = within(table).getAllByRole('row')
    const row = rows[1]
    expect(within(row).getByText('requirements.txt')).toBeInTheDocument()
    expect(within(row).getByText('cyclonedx-json')).toBeInTheDocument()
    expect(within(row).getByText('Completed')).toBeInTheDocument() // status badge
    expect(within(row).getByRole('link', { name: 'View' })).toHaveAttribute('href', '/results/abc-123')
  })

  it('shows the failure reason on a FAILED row', async () => {
    mockList.mockResolvedValue(page([{ ...JOB, status: 'FAILED', failure_reason: 'soft_timeout' }]))
    renderPage()

    expect(await screen.findByText('Failed')).toBeInTheDocument()
    expect(screen.getByText('soft_timeout')).toBeInTheDocument()
  })

  it('re-queries with the status filter and resets to page 1', async () => {
    mockList.mockResolvedValue(page([JOB]))
    renderPage()
    await screen.findByRole('table')

    await userEvent.click(screen.getByRole('combobox', { name: /status/i }))
    await userEvent.click(screen.getByRole('option', { name: 'Failed' }))

    expect(mockList).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'Failed', page: 1 }))
  })

  it('shows an empty state when there are no jobs', async () => {
    mockList.mockResolvedValue(page([], 0))
    renderPage()

    expect(await screen.findByText('No jobs yet.')).toBeInTheDocument()
  })

  it('does not poll rows that are already terminal (AC #5)', async () => {
    mockList.mockResolvedValue(page([JOB])) // SUCCESS
    renderPage()
    await screen.findByRole('table')

    expect(mockJobStatus).not.toHaveBeenCalled()
  })

  it('polls an in-progress row and shows live progress and phase', async () => {
    mockList.mockResolvedValue(page([{ ...JOB, status: 'PROGRESS' }]))
    mockJobStatus.mockResolvedValue(jobStatus())
    renderPage()

    expect(await screen.findByText(/vulnerability scan — 62%/)).toBeInTheDocument()
    expect(mockJobStatus).toHaveBeenCalledWith('abc-123')
  })

  it('swaps an in-progress row to its final failed state on transition', async () => {
    mockList.mockResolvedValue(page([{ ...JOB, status: 'PROGRESS' }]))
    mockJobStatus.mockResolvedValue(jobStatus({ status: 'FAILED', failure_reason: 'soft_timeout' }))
    renderPage()

    expect(await screen.findByText('Failed')).toBeInTheDocument()
    expect(screen.getByText('soft_timeout')).toBeInTheDocument()
  })
})
