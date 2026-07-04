import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SbomTab } from './SbomTab'
import { ApiError } from '../api/client'
import { getSbomDocument } from '../api/sbom'

vi.mock('../api/sbom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/sbom')>()
  return { ...actual, getSbomDocument: vi.fn() }
})
const mockGet = getSbomDocument as Mock

const DOC = {
  format: 'cyclonedx-json',
  components: [
    { name: 'django', version: '5.2.1', type: 'library', purl: null, license: 'BSD-3-Clause', relationship: null },
    { name: 'asgiref', version: '3.8.1', type: 'library', purl: null, license: null, relationship: null },
  ],
  raw: '{\n  "bomFormat": "CycloneDX"\n}',
}

describe('SbomTab', () => {
  it('renders the component table by default', async () => {
    mockGet.mockResolvedValue(DOC)
    render(<SbomTab taskId="t" />)

    const table = await screen.findByRole('table')
    expect(within(table).getByText('django')).toBeInTheDocument()
    expect(within(table).getByText('5.2.1')).toBeInTheDocument()
    expect(within(table).getByText('BSD-3-Clause')).toBeInTheDocument()
  })

  it('toggles to the raw document view', async () => {
    mockGet.mockResolvedValue(DOC)
    render(<SbomTab taskId="t" />)
    await screen.findByRole('table')

    await userEvent.click(screen.getByRole('button', { name: 'Raw' }))

    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByText(/"bomFormat": "CycloneDX"/)).toBeInTheDocument()
  })

  it('omits the relationship column until any component carries one', async () => {
    mockGet.mockResolvedValue(DOC)
    render(<SbomTab taskId="t" />)
    await screen.findByRole('table')

    expect(screen.queryByRole('columnheader', { name: 'Relationship' })).not.toBeInTheDocument()
  })

  it('shows the relationship column when components carry one (Story 8.4)', async () => {
    mockGet.mockResolvedValue({
      ...DOC,
      components: [
        { ...DOC.components[0], relationship: 'direct' },
        { ...DOC.components[1], relationship: 'transitive' },
      ],
    })
    render(<SbomTab taskId="t" />)

    const table = await screen.findByRole('table')
    expect(screen.getByRole('columnheader', { name: 'Relationship' })).toBeInTheDocument()
    expect(within(table).getByText('direct')).toBeInTheDocument()
    expect(within(table).getByText('transitive')).toBeInTheDocument()
  })

  it('shows an unavailable notice on a 404 (never produced or expired)', async () => {
    mockGet.mockRejectedValue(new ApiError('SBOM not available.', 404, 'not_ready'))
    render(<SbomTab taskId="t" />)

    expect(await screen.findByText(/not available for this job/i)).toBeInTheDocument()
  })
})
