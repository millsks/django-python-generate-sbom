import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ResultsPage } from './ResultsPage'
import { ApiError } from '../api/client'
import { getJobStatus } from '../api/jobs'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../api/jobs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/jobs')>()
  return { ...actual, getJobStatus: vi.fn() }
})
vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))

const mockStatus = getJobStatus as Mock
const mockAuth = useAuth as Mock
const AUTHED_WITH_ORG = {
  status: 'authed' as const,
  activeOrg: { slug: 'acme', name: 'Acme' },
  isAdmin: false,
  refresh: vi.fn(),
  logout: vi.fn(),
}

function renderPage() {
  render(
    <MemoryRouter initialEntries={['/results/abc-123']}>
      <Routes>
        <Route path="/results/:taskId" element={<ResultsPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

const SUCCESS = {
  task_id: 'abc-123',
  status: 'SUCCESS',
  progress: 100,
  current_phase: 'complete',
  failure_reason: null,
  result_url: '/api/v1/sbom/result/abc-123/',
  created_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
  artifacts_available: true,
  artifacts_expire_at: null,
}

describe('ResultsPage', () => {
  beforeEach(() => {
    mockStatus.mockReset()
    mockAuth.mockReturnValue(AUTHED_WITH_ORG)
  })

  it('renders the tabs in order with Overview active by default', async () => {
    mockStatus.mockResolvedValue(SUCCESS)
    renderPage()

    expect(await screen.findByRole('tab', { name: 'Overview' })).toBeInTheDocument()
    const tabs = screen.getAllByRole('tab')
    expect(tabs.map((t) => t.textContent)).toEqual([
      'Overview',
      'SBOM',
      'Vulnerabilities',
      'Licenses',
      'Version Currency',
      'Dependency Graph',
    ])
    expect(tabs[0]).toHaveAttribute('aria-selected', 'true')
    // MUI Button with href renders an anchor (role "link").
    expect(screen.getByRole('link', { name: 'Download SBOM' })).toHaveAttribute(
      'href',
      '/api/v1/sbom/result/abc-123/',
    )
  })

  it('renders an access-denied state (not tabs) on a 403/404', async () => {
    mockStatus.mockRejectedValue(new ApiError('Job not found.', 404, 'not_found'))
    renderPage()

    expect(await screen.findByText(/don't have access/i)).toBeInTheDocument()
    expect(screen.queryByRole('tab')).not.toBeInTheDocument()
  })

  it('shows an expired-artifacts notice with retained metadata (no tabs) when artifacts are gone', async () => {
    mockStatus.mockResolvedValue({
      ...SUCCESS,
      result_url: null,
      artifacts_available: false,
      artifacts_expire_at: '2026-02-01T00:00:00Z',
    })
    renderPage()

    expect(await screen.findByText(/no longer available/i)).toBeInTheDocument()
    // The retained summary metadata (Overview) stays visible…
    expect(screen.getByText('Total packages')).toBeInTheDocument()
    // …but the artifact-backed tabs and the download are gone.
    expect(screen.queryByRole('tab')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Download SBOM' })).not.toBeInTheDocument()
  })
})
