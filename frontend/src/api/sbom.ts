// SBOM document content for the in-app viewer (Story 8.6). The backend parses the
// stored SBOM (cdx-json / cdx-xml / spdx) into a normalized component list and
// returns the raw document text, so the SPA needs no format-specific parser (AD-5).
import { apiRequest } from './client'

export interface SbomComponent {
  name: string
  version: string
  type: string | null
  purl: string | null
  license: string | null
  relationship: string | null // direct | transitive — populated by Stories 8.3/8.4
}

export interface SbomDocument {
  format: string // serializer id: cyclonedx-json | cyclonedx-xml | spdx-json
  components: SbomComponent[]
  raw: string // the exact document text, pretty-printed
}

export function getSbomDocument(taskId: string): Promise<SbomDocument> {
  return apiRequest<SbomDocument>(`/sbom/document/${taskId}/`)
}
