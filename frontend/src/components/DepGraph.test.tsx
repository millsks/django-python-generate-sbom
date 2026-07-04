import { describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { createElement } from 'react'
import { render, screen } from '@testing-library/react'
import { DepGraph } from './DepGraph'
import { ApiError } from '../api/client'
import { getGraph } from '../api/reports'

// Cytoscape needs a real canvas; mock it and the wrapper for jsdom.
vi.mock('cytoscape', () => ({ default: { use: vi.fn() } }))
vi.mock('cytoscape-dagre', () => ({ default: {} }))
vi.mock('react-cytoscapejs', () => {
  const Comp = (props: { elements: unknown[]; layout: { name: string } }) =>
    createElement('div', {
      'data-testid': 'cyto',
      'data-layout': props.layout.name,
      'data-count': String(props.elements.length),
    })
  Comp.normalizeElements = (data: { nodes: unknown[]; edges: unknown[] }) => [...data.nodes, ...data.edges]
  return { default: Comp }
})
vi.mock('../api/reports', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/reports')>()
  return { ...actual, getGraph: vi.fn() }
})
const mockGet = getGraph as Mock

const GRAPH = {
  nodes: [
    { data: { id: 'a==1', label: 'a', version: '1' } },
    { data: { id: 'b==2', label: 'b', version: '2' } },
  ],
  edges: [{ data: { source: 'a==1', target: 'b==2' } }],
}

describe('DepGraph', () => {
  it('passes normalized elements and the dagre layout to Cytoscape (no PyVis/iframe)', async () => {
    mockGet.mockResolvedValue(GRAPH)
    render(<DepGraph taskId="t" />)

    const cyto = await screen.findByTestId('cyto')
    expect(cyto).toHaveAttribute('data-layout', 'dagre')
    expect(cyto).toHaveAttribute('data-count', '3') // 2 nodes + 1 edge
    expect(document.querySelector('iframe')).toBeNull() // AD-9: no PyVis iframe
  })

  it('offers a static SVG download', async () => {
    mockGet.mockResolvedValue(GRAPH)
    render(<DepGraph taskId="t" />)

    const link = await screen.findByRole('link', { name: 'Download SVG' })
    expect(link).toHaveAttribute('href', '/api/v1/sbom/result/t/reports/graph/download/')
  })

  it('shows a direct/transitive legend when nodes carry a relationship (Story 8.5)', async () => {
    mockGet.mockResolvedValue({
      nodes: [
        { data: { id: 'a==1', label: 'a', version: '1', relationship: 'direct' } },
        { data: { id: 'b==2', label: 'b', version: '2', relationship: 'transitive' } },
      ],
      edges: [{ data: { source: 'a==1', target: 'b==2' } }],
    })
    render(<DepGraph taskId="t" />)

    expect(await screen.findByText('Direct')).toBeInTheDocument()
    expect(screen.getByText('Transitive')).toBeInTheDocument()
  })

  it('omits the legend for older graphs without relationship data (graceful, AC #4)', async () => {
    mockGet.mockResolvedValue(GRAPH)
    render(<DepGraph taskId="t" />)

    await screen.findByTestId('cyto')
    expect(screen.queryByText('Direct')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('graph legend')).not.toBeInTheDocument()
  })

  it('renders the failure notice when the report failed', async () => {
    mockGet.mockRejectedValue(new ApiError('failed', 404, 'report_failed', 'graphviz down'))
    render(<DepGraph taskId="t" />)

    expect(await screen.findByText(/could not be generated/i)).toBeInTheDocument()
    expect(screen.getByText(/graphviz down/i)).toBeInTheDocument()
  })
})
