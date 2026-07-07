import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SbomTab } from './SbomTab'
import { ApiError } from '../api/client'
import { getSbomDocument } from '../api/sbom'
import { downloadWorkbook } from '../excelExport'

vi.mock('../api/sbom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/sbom')>()
  return { ...actual, getSbomDocument: vi.fn() }
})
vi.mock('../excelExport', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../excelExport')>()
  return { ...actual, downloadWorkbook: vi.fn() }
})
const mockGet = getSbomDocument as Mock
const mockDownload = downloadWorkbook as Mock

const DOC = {
  format: 'cyclonedx-json',
  components: [
    {
      name: 'django',
      version: '5.2.1',
      type: 'library',
      purl: 'pkg:pypi/django@5.2.1',
      license: 'BSD-3-Clause',
      relationship: null,
      ecosystem: 'pypi',
    },
    {
      name: 'asgiref',
      version: '3.8.1',
      type: 'library',
      purl: 'pkg:conda/asgiref@3.8.1',
      license: null,
      relationship: null,
      ecosystem: 'conda',
    },
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
    // Default sort is by package name, ascending (Story 8.16): asgiref before django.
    const [, ...rows] = within(table).getAllByRole('row')
    expect(within(rows[0]).getByText('asgiref')).toBeInTheDocument()
  })

  it('renders — for a component with no license (Story 8.25)', async () => {
    mockGet.mockResolvedValue(DOC)
    render(<SbomTab taskId="t" />)

    const table = await screen.findByRole('table')
    const asgirefRow = within(table).getByText('asgiref').closest('tr') as HTMLElement
    // asgiref carries license: null — its only em-dash cell is the License column.
    expect(within(asgirefRow).getByText('—')).toBeInTheDocument()
  })

  it('renders the ecosystem column (Story 8.26)', async () => {
    mockGet.mockResolvedValue(DOC)
    render(<SbomTab taskId="t" />)

    const table = await screen.findByRole('table')
    expect(within(table).getByRole('columnheader', { name: 'Ecosystem' })).toBeInTheDocument()
    const djangoRow = within(table).getByText('django').closest('tr') as HTMLElement
    expect(within(djangoRow).getByText('pypi')).toBeInTheDocument()
    const asgirefRow = within(table).getByText('asgiref').closest('tr') as HTMLElement
    expect(within(asgirefRow).getByText('conda')).toBeInTheDocument()
  })

  it('exports the components to Excel from the Components view (Story 8.27)', async () => {
    mockGet.mockResolvedValue(DOC)
    mockDownload.mockClear()
    render(<SbomTab taskId="t" />)
    await screen.findByRole('table')

    await userEvent.click(screen.getByRole('button', { name: 'Export to Excel' }))

    expect(mockDownload).toHaveBeenCalledWith(expect.anything(), 'sbom-components.xlsx')
  })

  it('shows no Excel export in the Raw view (Story 8.27)', async () => {
    mockGet.mockResolvedValue(DOC)
    render(<SbomTab taskId="t" />)
    await screen.findByRole('table')

    await userEvent.click(screen.getByRole('button', { name: 'Raw' }))

    expect(screen.queryByRole('button', { name: 'Export to Excel' })).not.toBeInTheDocument()
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

  it('renders the metadata block with provenance and document info (Story 8.11)', async () => {
    mockGet.mockResolvedValue({
      ...DOC,
      metadata: {
        component_name: 'web',
        application_id: 'APP-1',
        repository_url: 'https://github.com/acme/web',
        source_branch: 'main',
        format: 'CycloneDX',
        spec_version: '1.6',
        generated: '2026-07-04T20:00:00Z',
      },
    })
    render(<SbomTab taskId="t" />)
    await screen.findByRole('table')

    const meta = screen.getByLabelText('SBOM metadata')
    expect(within(meta).getByText('web')).toBeInTheDocument()
    expect(within(meta).getByText('APP-1')).toBeInTheDocument()
    expect(within(meta).getByText('https://github.com/acme/web')).toBeInTheDocument()
    expect(within(meta).getByText('main')).toBeInTheDocument()
    expect(within(meta).getByText('CycloneDX 1.6')).toBeInTheDocument()
  })

  it('omits absent metadata fields (Story 8.11)', async () => {
    mockGet.mockResolvedValue({
      ...DOC,
      metadata: { component_name: 'web', format: 'SPDX', spec_version: '2.3' },
    })
    render(<SbomTab taskId="t" />)
    await screen.findByRole('table')

    const meta = screen.getByLabelText('SBOM metadata')
    expect(within(meta).getByText('web')).toBeInTheDocument()
    expect(within(meta).getByText('SPDX 2.3')).toBeInTheDocument()
    expect(within(meta).queryByText('Repository')).not.toBeInTheDocument()
    expect(within(meta).queryByText('Branch')).not.toBeInTheDocument()
    expect(within(meta).queryByText('Application ID')).not.toBeInTheDocument()
  })

  it('renders no metadata block when metadata is absent', async () => {
    mockGet.mockResolvedValue(DOC)
    render(<SbomTab taskId="t" />)
    await screen.findByRole('table')

    expect(screen.queryByLabelText('SBOM metadata')).not.toBeInTheDocument()
  })

  it('shows an unavailable notice on a 404 (never produced or expired)', async () => {
    mockGet.mockRejectedValue(new ApiError('SBOM not available.', 404, 'not_ready'))
    render(<SbomTab taskId="t" />)

    expect(await screen.findByText(/not available for this job/i)).toBeInTheDocument()
  })
})
