import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { HistoryPage } from './HistoryPage'
import { bulkDeleteArtifacts, deleteJobArtifacts, getJobStatus, listJobs } from '../api/jobs'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../api/jobs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/jobs')>()
  return {
    ...actual,
    listJobs: vi.fn(),
    getJobStatus: vi.fn(),
    deleteJobArtifacts: vi.fn(),
    bulkDeleteArtifacts: vi.fn(),
  }
})
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))

const mockList = listJobs as Mock
const mockJobStatus = getJobStatus as Mock
const mockDelete = deleteJobArtifacts as Mock
const mockBulk = bulkDeleteArtifacts as Mock
const mockAuth = useAuth as Mock

beforeEach(() => {
  // Default: a signed-in non-admin. Admin-only affordances are opt-in per test.
  mockAuth.mockReturnValue({ status: 'authed', activeOrg: null, isAdmin: false, refresh: vi.fn(), logout: vi.fn() })
  mockDelete.mockResolvedValue({ task_id: 'abc-123', deleted: true })
  mockBulk.mockResolvedValue({ deleted: 1 })
})

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
  elapsed_seconds: 83,
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

  it('shows the formatted elapsed time for a finished job', async () => {
    mockList.mockResolvedValue(page([JOB])) // elapsed_seconds: 83
    renderPage()

    const table = await screen.findByRole('table')
    expect(within(table).getByText('Elapsed')).toBeInTheDocument() // column header
    expect(within(within(table).getAllByRole('row')[1]).getByText('1m 23s')).toBeInTheDocument()
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

  it('deletes a single job’s artifacts after confirmation and refreshes', async () => {
    mockList.mockResolvedValue(page([JOB]))
    renderPage()
    await screen.findByRole('table')

    await userEvent.click(screen.getByRole('button', { name: /delete artifacts for requirements\.txt/i }))
    // A confirmation dialog opens; only on confirm does the API fire.
    expect(mockDelete).not.toHaveBeenCalled()
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }))

    expect(mockDelete).toHaveBeenCalledWith('abc-123')
    expect(mockList.mock.calls.length).toBeGreaterThan(1) // re-fetched after delete
  })

  it('bulk-deletes the selected jobs’ artifacts', async () => {
    mockList.mockResolvedValue(page([JOB]))
    renderPage()
    await screen.findByRole('table')

    await userEvent.click(screen.getByRole('checkbox', { name: /select requirements\.txt/i }))
    await userEvent.click(screen.getByRole('button', { name: /delete selected \(1\)/i }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }))

    expect(mockBulk).toHaveBeenCalledWith({ taskIds: ['abc-123'] })
  })

  it('offers org-wide delete to admins and calls the all-org endpoint', async () => {
    mockAuth.mockReturnValue({ status: 'authed', activeOrg: null, isAdmin: true, refresh: vi.fn(), logout: vi.fn() })
    mockList.mockResolvedValue(page([JOB]))
    renderPage()
    await screen.findByRole('table')

    await userEvent.click(screen.getByRole('button', { name: /delete all artifacts/i }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }))

    expect(mockBulk).toHaveBeenCalledWith({ all: true })
  })

  it('hides the org-wide delete button from non-admins', async () => {
    mockList.mockResolvedValue(page([JOB]))
    renderPage()
    await screen.findByRole('table')

    expect(screen.queryByRole('button', { name: /delete all artifacts/i })).not.toBeInTheDocument()
  })
})
