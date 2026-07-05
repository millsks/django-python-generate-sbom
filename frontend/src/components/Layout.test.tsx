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
  beforeEach(() => mockGetOrgs.mockResolvedValue([])) // OrgSwitcher renders nothing

  it('wraps the routed page and shows authed nav (no admin links)', async () => {
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

  it('shows Login/Register (and no app links) when logged out', async () => {
    mockUseAuth.mockReturnValue(authState({ status: 'anon', activeOrg: null }))
    renderAt('/login')

    expect(screen.getByRole('link', { name: 'Login' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Register' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Upload' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: /main navigation/i })).not.toBeInTheDocument()
  })

  it('marks the active route', async () => {
    mockUseAuth.mockReturnValue(authState())
    renderAt('/upload')
    expect(screen.getByRole('link', { name: 'Upload' })).toHaveClass('active')
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

  it('logs out from the account menu', async () => {
    const logout = vi.fn().mockResolvedValue(undefined)
    mockUseAuth.mockReturnValue(authState({ logout }))
    renderAt()

    await userEvent.click(screen.getByRole('button', { name: /account menu/i }))
    await userEvent.click(screen.getByRole('menuitem', { name: 'Logout' }))
    expect(logout).toHaveBeenCalled()
  })
})
