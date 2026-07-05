import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SideNav } from './SideNav'

function renderNav(isAdmin: boolean) {
  return render(
    <MemoryRouter>
      <SideNav isAdmin={isAdmin} activeOrg={{ slug: 'acme', name: 'Acme' }} />
    </MemoryRouter>,
  )
}

describe('SideNav', () => {
  it('shows the admin-only Organization entry for an admin (Story 2.11)', () => {
    renderNav(true)
    expect(screen.getByRole('link', { name: /organization/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /members/i })).toBeInTheDocument()
  })

  it('orders destinations Upload, History, Members, API Keys, Organization for an admin (Story 2.15)', () => {
    renderNav(true)
    const labels = screen.getAllByRole('link').map((link) => link.textContent)
    expect(labels).toEqual(['Upload', 'History', 'Members', 'API Keys', 'Organization'])
  })

  it('hides the Organization entry for a non-admin', () => {
    renderNav(false)
    expect(screen.queryByRole('link', { name: /organization/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /members/i })).not.toBeInTheDocument()
    // Non-admin still sees the base destinations.
    expect(screen.getByRole('link', { name: /upload/i })).toBeInTheDocument()
  })
})
