// Dependency Graph tab (Story 5.5): an interactive Cytoscape.js graph with a
// hierarchical dagre layout, consuming the {nodes, edges} JSON (AD-9 — no PyVis
// HTML, no iframe), plus a static SVG download. Lazy-mounted via the shell.
import { useEffect, useState } from 'react'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import CytoscapeComponent from 'react-cytoscapejs'
import type { Core } from 'cytoscape'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Typography from '@mui/material/Typography'
import { ApiError } from '../api/client'
import { getGraph, graphSvgDownloadUrl, type GraphReport } from '../api/reports'
import { TabFailureNotice } from './TabFailureNotice'

// Register the dagre layout extension once at module load.
cytoscape.use(dagre)

const STYLESHEET = [
  { selector: 'node', style: { label: 'data(label)', 'font-size': 10, 'background-color': '#1976d2' } },
  { selector: 'edge', style: { width: 1, 'line-color': '#bbb', 'target-arrow-color': '#bbb', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier' } },
  { selector: '.highlight', style: { 'background-color': '#ff5722', 'line-color': '#ff5722', 'target-arrow-color': '#ff5722' } },
]

function wireHoverHighlight(cy: Core) {
  cy.on('mouseover', 'node', (event) => {
    const node = event.target
    node.addClass('highlight')
    node.connectedEdges().addClass('highlight')
  })
  cy.on('mouseout', 'node', (event) => {
    const node = event.target
    node.removeClass('highlight')
    node.connectedEdges().removeClass('highlight')
  })
}

export function DepGraph({ taskId }: { taskId: string }) {
  const [graph, setGraph] = useState<GraphReport | null>(null)
  const [failure, setFailure] = useState<{ reason: string | null } | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    getGraph(taskId).then(
      (data) => active && setGraph(data),
      (err: unknown) => {
        if (!active) return
        if (err instanceof ApiError && err.code === 'report_failed') setFailure({ reason: err.failureReason ?? null })
        else setError(true)
      },
    )
    return () => {
      active = false
    }
  }, [taskId])

  if (failure) return <TabFailureNotice reason={failure.reason} />
  if (error) return <Alert severity="error">Could not load the dependency graph.</Alert>
  if (!graph) return <CircularProgress aria-label="Loading dependency graph" />

  const elements = CytoscapeComponent.normalizeElements({ nodes: graph.nodes, edges: graph.edges })

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box>
        <Button variant="outlined" href={graphSvgDownloadUrl(taskId)}>
          Download SVG
        </Button>
      </Box>
      {graph.nodes.length === 0 ? (
        <Alert severity="info">No dependency data to graph.</Alert>
      ) : (
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1 }}>
          <CytoscapeComponent
            elements={elements}
            layout={{ name: 'dagre', rankDir: 'TB' }}
            stylesheet={STYLESHEET}
            style={{ width: '100%', height: 600 }}
            cy={wireHoverHighlight}
          />
        </Box>
      )}
      <Typography variant="caption" color="text.secondary">
        {graph.nodes.length} nodes · {graph.edges.length} edges
      </Typography>
    </Box>
  )
}
