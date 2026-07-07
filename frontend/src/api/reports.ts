// Analysis-report API calls (vulnerabilities, licenses, versions).
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

export interface VersionEntry {
  name: string
  installed: string
  latest: string | null
  currency: string
  lts: string | null // the tracked LTS series for this package, or null if untracked
  on_lts: boolean | null // whether the installed version is on that LTS series; null if untracked
  ecosystem?: string // "pypi" | "conda" — the package's source registry (Story 8.8)
  conda_latest?: string | null // latest version on conda-forge (via prefix.dev), or null (Story 8.10)
  latest_mismatch?: boolean // true when the PyPI latest and conda-forge latest diverge (Story 8.10)
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

export function getVersions(taskId: string): Promise<VersionReport> {
  return apiRequest<VersionReport>(`${base(taskId)}/versions/`)
}
