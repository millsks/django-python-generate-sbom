import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { HomePage } from './HomePage'
import { APP_NAME, DOCS_URL } from '../config'
import { NO_ORG_MESSAGE } from '../components/NoOrgState'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockAuth = useAuth as Mock
const authState = (over: Record<string, unknown> = {}) => ({
  status: 'authed',
  activeOrg: { slug: 'acme', name: 'Acme' },
  isGlobalAdmin: false,
  ...over,
})

function renderPage() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  // Default: an anonymous visitor sees the full landing page (with the CTA).
  mockAuth.mockReturnValue(authState({ status: 'anon', activeOrg: null }))
})

describe('HomePage', () => {
  it('shows the hero with the app name and the primary upload CTA to /upload', () => {
    renderPage()
    expect(screen.getByRole('heading', { level: 1, name: APP_NAME })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /upload a manifest/i })).toHaveAttribute('href', '/upload')
  })

  it('links to the documentation site', () => {
    renderPage()
    expect(screen.getByRole('link', { name: /read the docs/i })).toHaveAttribute('href', DOCS_URL)
  })

  it('renders the feature tiles and the how-it-works section', () => {
    renderPage()
    expect(screen.getByRole('heading', { name: /what you get/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /vulnerability report/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /version currency/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /how it works/i })).toBeInTheDocument()
  })

  it('shows the CTA for a signed-in user with an active org', () => {
    mockAuth.mockReturnValue(authState({ activeOrg: { slug: 'acme', name: 'Acme' } }))
    renderPage()
    expect(screen.getByRole('link', { name: /upload a manifest/i })).toBeInTheDocument()
  })

  it('hides the CTA and shows the no-org state for a zero-org user (Story 2.18)', () => {
    mockAuth.mockReturnValue(authState({ activeOrg: null }))
    renderPage()
    expect(screen.queryByRole('link', { name: /upload a manifest/i })).not.toBeInTheDocument()
    expect(screen.getByText(NO_ORG_MESSAGE)).toBeInTheDocument()
  })
})
