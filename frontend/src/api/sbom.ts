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

// Document metadata block shown above the component table (Story 8.11). The backend reads
// the provenance already embedded in the SBOM plus the format/spec version/timestamp;
// absent fields are omitted, so every field is optional.
export interface SbomMetadata {
  component_name?: string
  application_id?: string
  repository_url?: string
  source_branch?: string
  format?: string // human name: CycloneDX | SPDX
  spec_version?: string // e.g. 1.6 (CycloneDX) or 2.3 (SPDX)
  generated?: string // serialized timestamp
}

export interface SbomDocument {
  format: string // serializer id: cyclonedx-json | cyclonedx-xml | spdx-json
  metadata?: SbomMetadata // parsed document metadata (Story 8.11)
  components: SbomComponent[]
  raw: string // the exact document text, pretty-printed
}

export function getSbomDocument(taskId: string): Promise<SbomDocument> {
  return apiRequest<SbomDocument>(`/sbom/document/${taskId}/`)
}
