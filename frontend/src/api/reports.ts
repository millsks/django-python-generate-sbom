// Analysis-report API calls (vulnerabilities, licenses, graph, versions).
// Implemented in Epic 4; consumed by the results tabs (5.2-5.6). All calls go
// through the shared client (AD-5). A failed report surfaces as an ApiError with
// code "report_failed" and a failureReason.
import { apiRequest } from './client'

const base = (taskId: string) => `/sbom/result/${taskId}/reports`

export interface VulnerabilityEntry {
  id: string
  aliases: string[]
  cve: string | null
  cvss_score: number | null
  severity: string
  advisory_url: string
  cwe: string[]
}

export interface VulnerablePackage {
  name: string
  version: string
  vulnerabilities: VulnerabilityEntry[]
}

export interface VulnerabilityReport {
  packages: VulnerablePackage[]
  summary: { vulnerable_package_count: number; severity_breakdown: Record<string, number> }
}

export interface LicenseTier {
  tier: string
  packages: { name: string; version: string; license: string }[]
}

export interface LicenseReport {
  tiers: LicenseTier[]
  summary: Record<string, number>
}

export interface GraphNode {
  data: { id: string; label: string; version: string }
}

export interface GraphEdge {
  data: { source: string; target: string }
}

export interface GraphReport {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface VersionEntry {
  name: string
  installed: string
  latest: string | null
  currency: string
  lts: string | null
}

export interface VersionReport {
  packages: VersionEntry[]
  summary: Record<string, number>
}

export function getVulnerabilities(taskId: string): Promise<VulnerabilityReport> {
  return apiRequest<VulnerabilityReport>(`${base(taskId)}/vulnerabilities/`)
}

export function getLicenses(taskId: string): Promise<LicenseReport> {
  return apiRequest<LicenseReport>(`${base(taskId)}/licenses/`)
}

export function getGraph(taskId: string): Promise<GraphReport> {
  return apiRequest<GraphReport>(`${base(taskId)}/graph/`)
}

// The graph SVG is a genuine file download (303 → presigned URL); the browser
// follows the redirect when navigated to this path.
export function graphSvgDownloadUrl(taskId: string): string {
  return `/api/v1${base(taskId)}/graph/download/`
}

export function getVersions(taskId: string): Promise<VersionReport> {
  return apiRequest<VersionReport>(`${base(taskId)}/versions/`)
}
