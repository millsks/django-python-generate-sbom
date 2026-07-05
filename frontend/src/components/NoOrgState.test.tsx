import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NoOrgState, NO_ORG_MESSAGE } from './NoOrgState'

describe('NoOrgState', () => {
  it('shows the no-org message and a create-org affordance', () => {
    render(<NoOrgState />)
    expect(screen.getByText(NO_ORG_MESSAGE)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create organization/i })).toBeInTheDocument()
  })

  it('opens the create-org dialog when the affordance is clicked', async () => {
    const user = userEvent.setup()
    render(<NoOrgState />)

    await user.click(screen.getByRole('button', { name: /create organization/i }))

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByLabelText(/organization name/i)).toBeInTheDocument()
  })
})
