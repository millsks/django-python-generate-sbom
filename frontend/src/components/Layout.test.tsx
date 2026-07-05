import { describe, expect, it, vi, beforeEach } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './Layout'
import { useAuth } from '../auth/AuthProvider'
import { getOrgs } from '../api/orgs'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))
const mockUseAuth = useAuth as Mock

// Stub the theme toggle so the layout test doesn't depend on the theme provider
// (and its localStorage access) — keeps it isolated from cross-file test state.
vi.mock('../ThemeModeProvider', () => ({ ThemeToggle: () => <button aria-label="Toggle light/dark theme" /> }))

// Drive responsiveness deterministically: default desktop (false); a test flips it to
// mobile (true) to exercise the hamburger + temporary drawer.
vi.mock('@mui/material/useMediaQuery', () => ({ default: vi.fn() }))
import useMediaQuery from '@mui/material/useMediaQuery'
const mockUseMediaQuery = useMediaQuery as unknown as Mock

vi.mock('../api/orgs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/orgs')>()
  return { ...actual, getOrgs: vi.fn() }
})
const mockGetOrgs = getOrgs as Mock

type Auth = ReturnType<typeof useAuth>
const authState = (over: Partial<Auth> = {}): Auth => ({
  status: 'authed',
  activeOrg: { slug: 'acme', name: 'Acme' },
  isAdmin: false,
  refresh: vi.fn(),
  logout: vi.fn(),
  ...over,
})

function renderAt(path = '/upload') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/upload" element={<div>upload page</div>} />
          <Route path="/login" element={<div>login page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('Layout', () => {
  beforeEach(() => {
    mockGetOrgs.mockResolvedValue([]) // OrgSwitcher renders nothing
    mockUseMediaQuery.mockReturnValue(false) // desktop by default
  })

  it('wraps the routed page and shows authed nav in the side drawer (no admin links)', async () => {
    mockUseAuth.mockReturnValue(authState())
    renderAt('/upload')

    expect(screen.getByText('upload page')).toBeInTheDocument() // Outlet content
    const nav = screen.getByRole('navigation', { name: /main navigation/i })
    expect(within(nav).getByRole('link', { name: 'Upload' })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'History' })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'API Keys' })).toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'Members' })).not.toBeInTheDocument()
  })

  it('shows Members only for admins', async () => {
    mockUseAuth.mockReturnValue(authState({ isAdmin: true }))
    renderAt()
    expect(screen.getByRole('link', { name: 'Members' })).toBeInTheDocument()
  })

  it('shows Login/Register (and no app nav) when logged out', async () => {
    mockUseAuth.mockReturnValue(authState({ status: 'anon', activeOrg: null }))
    renderAt('/login')

    expect(screen.getByRole('link', { name: 'Login' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Register' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Upload' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: /main navigation/i })).not.toBeInTheDocument()
  })

  it('marks the active destination', async () => {
    mockUseAuth.mockReturnValue(authState())
    renderAt('/upload')
    expect(screen.getByRole('link', { name: 'Upload' })).toHaveClass('active')
  })

  it('surfaces the active org as contextual side info', async () => {
    mockUseAuth.mockReturnValue(authState())
    renderAt('/upload')
    const nav = screen.getByRole('navigation', { name: /main navigation/i })
    // The side region sits alongside the nav in the drawer.
    expect(within(nav.parentElement as HTMLElement).getByText('Acme')).toBeInTheDocument()
  })

  it('uses a permanent side nav (no hamburger) on desktop', async () => {
    mockUseAuth.mockReturnValue(authState())
    renderAt('/upload')
    expect(screen.queryByRole('button', { name: /open navigation/i })).not.toBeInTheDocument()
  })

  it('collapses to a hamburger-toggled drawer on small screens', async () => {
    mockUseMediaQuery.mockReturnValue(true) // mobile
    mockUseAuth.mockReturnValue(authState())
    renderAt('/upload')

    const burger = screen.getByRole('button', { name: /open navigation/i })
    expect(burger).toBeInTheDocument()
    await userEvent.click(burger)
    const nav = screen.getByRole('navigation', { name: /main navigation/i })
    expect(within(nav).getByRole('link', { name: 'Upload' })).toBeInTheDocument()
  })

  it('shows repo and docs links in the header with correct href/target/label (authed)', async () => {
    mockUseAuth.mockReturnValue(authState())
    renderAt('/upload')

    const repo = screen.getByRole('link', { name: 'GitHub repository' })
    expect(repo).toHaveAttribute('href', 'https://github.com/millsks/django-python-generate-sbom')
    expect(repo).toHaveAttribute('target', '_blank')
    expect(repo).toHaveAttribute('rel', 'noopener noreferrer')

    const docs = screen.getByRole('link', { name: 'Documentation' })
    expect(docs).toHaveAttribute('href', 'https://millsks.github.io/django-python-generate-sbom/')
    expect(docs).toHaveAttribute('target', '_blank')
    expect(docs).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('shows repo and docs links when logged out too', async () => {
    mockUseAuth.mockReturnValue(authState({ status: 'anon', activeOrg: null }))
    renderAt('/login')
    expect(screen.getByRole('link', { name: 'GitHub repository' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Documentation' })).toBeInTheDocument()
  })

  it('renders a footer with app name, version, and doc/repo/license links', async () => {
    mockUseAuth.mockReturnValue(authState())
    renderAt('/upload')

    const footer = screen.getByRole('contentinfo')
    expect(within(footer).getByText(/Generate SBOM v0\.1\.0/)).toBeInTheDocument()
    expect(within(footer).getByRole('link', { name: 'Docs' })).toHaveAttribute(
      'href',
      'https://millsks.github.io/django-python-generate-sbom/',
    )
    expect(within(footer).getByRole('link', { name: 'GitHub' })).toHaveAttribute(
      'href',
      'https://github.com/millsks/django-python-generate-sbom',
    )
    expect(within(footer).getByRole('link', { name: 'License' })).toHaveAttribute(
      'href',
      'https://github.com/millsks/django-python-generate-sbom/blob/main/LICENSE',
    )
  })

  it('logs out from the account menu', async () => {
    const logout = vi.fn().mockResolvedValue(undefined)
    mockUseAuth.mockReturnValue(authState({ logout }))
    renderAt()

    await userEvent.click(screen.getByRole('button', { name: /account menu/i }))
    await userEvent.click(screen.getByRole('menuitem', { name: 'Logout' }))
    expect(logout).toHaveBeenCalled()
  })
})
