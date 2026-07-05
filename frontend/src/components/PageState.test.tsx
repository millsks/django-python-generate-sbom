import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import HistoryIcon from '@mui/icons-material/History'
import { EmptyState, ErrorState, LoadingState } from './PageState'

describe('PageState', () => {
  it('LoadingState renders an accessible busy indicator', () => {
    render(<LoadingState label="Loading jobs" />)
    expect(screen.getByLabelText('Loading jobs')).toBeInTheDocument()
  })

  it('EmptyState renders the title, message, and optional icon', () => {
    render(<EmptyState title="No jobs yet" message="Upload a manifest to get started." icon={HistoryIcon} />)
    expect(screen.getByText('No jobs yet')).toBeInTheDocument()
    expect(screen.getByText('Upload a manifest to get started.')).toBeInTheDocument()
    expect(screen.getByTestId('HistoryIcon')).toBeInTheDocument()
  })

  it('ErrorState renders a titled error alert', () => {
    render(<ErrorState message="Could not load your jobs." />)
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Something went wrong')
    expect(alert).toHaveTextContent('Could not load your jobs.')
  })
})
