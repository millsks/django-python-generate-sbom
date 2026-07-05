import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SideNav } from './SideNav'

function renderNav(isAdmin: boolean, initialPath = '/', isGlobalAdmin = false) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <SideNav isAdmin={isAdmin} isGlobalAdmin={isGlobalAdmin} activeOrg={{ slug: 'acme', name: 'Acme' }} />
    </MemoryRouter>,
  )
}

describe('SideNav', () => {
  it('shows the admin-only Organization entry for an admin (Story 2.11)', () => {
    renderNav(true)
    expect(screen.getByRole('link', { name: /organization/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /members/i })).toBeInTheDocument()
  })

  it('orders destinations Home, Upload, History, Members, API Keys, Organization for an admin (Stories 2.15, 10.8)', () => {
    renderNav(true)
    const labels = screen.getAllByRole('link').map((link) => link.textContent)
    expect(labels).toEqual(['Home', 'Upload', 'History', 'Members', 'API Keys', 'Organization'])
  })

  it('shows Home, Upload, History, API Keys for a non-admin (no admin links)', () => {
    renderNav(false)
    const labels = screen.getAllByRole('link').map((link) => link.textContent)
    expect(labels).toEqual(['Home', 'Upload', 'History', 'API Keys'])
    expect(screen.queryByRole('link', { name: /organization/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /members/i })).not.toBeInTheDocument()
  })

  it('shows a global-admin-only "Global Admins" entry for a global admin (Story 13.1)', () => {
    renderNav(true, '/', true)
    expect(screen.getByRole('link', { name: /global admins/i })).toHaveAttribute('href', '/platform/global-admins')
  })

  it('hides "Global Admins" for a non-global-admin', () => {
    renderNav(true, '/', false)
    expect(screen.queryByRole('link', { name: /global admins/i })).not.toBeInTheDocument()
  })

  it('marks Home active only on the index route', () => {
    renderNav(false, '/')
    // NavLink sets aria-current="page" on the active link.
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Upload' })).not.toHaveAttribute('aria-current')
  })

  it('does not mark Home active on a sub-route (the `end` prop)', () => {
    renderNav(false, '/upload')
    expect(screen.getByRole('link', { name: 'Home' })).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('link', { name: 'Upload' })).toHaveAttribute('aria-current', 'page')
  })
})
