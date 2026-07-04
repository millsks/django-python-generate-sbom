import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TabFailureNotice } from './TabFailureNotice'

describe('TabFailureNotice', () => {
  it('shows the failure reason when provided', () => {
    render(<TabFailureNotice reason="osv unavailable" />)
    expect(screen.getByText(/could not be generated/i)).toBeInTheDocument()
    expect(screen.getByText(/osv unavailable/i)).toBeInTheDocument()
  })

  it('falls back to a generic message when no reason is given', () => {
    render(<TabFailureNotice reason={null} />)
    expect(screen.getByText(/the analysis phase failed/i)).toBeInTheDocument()
  })
})
