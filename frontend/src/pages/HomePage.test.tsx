import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { HomePage } from './HomePage'
import { APP_NAME, DOCS_URL } from '../config'

function renderPage() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  )
}

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
})
