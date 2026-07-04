// Minimal ambient types for react-cytoscapejs (the package ships no declarations).
declare module 'react-cytoscapejs' {
  import type { ComponentType } from 'react'
  import type { Core, ElementDefinition } from 'cytoscape'

  interface CytoscapeComponentProps {
    elements: ElementDefinition[]
    layout?: Record<string, unknown>
    style?: Record<string, unknown>
    stylesheet?: unknown[]
    cy?: (cy: Core) => void
    [key: string]: unknown
  }

  const CytoscapeComponent: ComponentType<CytoscapeComponentProps> & {
    normalizeElements(data: { nodes: unknown[]; edges: unknown[] }): ElementDefinition[]
  }

  export default CytoscapeComponent
}
