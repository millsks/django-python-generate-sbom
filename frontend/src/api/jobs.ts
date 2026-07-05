// Job-related API calls. Expanded in Epic 3 (submission) and Epic 6 (history).
import { apiRequest, apiUpload } from './client'

// Output-format choices accepted by POST /sbom/generate/ (server OUTPUT_FORMAT_MAP).
export const OUTPUT_FORMATS = [
  { value: 'cdx-json', label: 'CycloneDX (JSON)' },
  { value: 'cdx-xml', label: 'CycloneDX (XML)' },
  { value: 'spdx-2.3', label: 'SPDX (JSON)' },
] as const

export const DEFAULT_OUTPUT_FORMAT = 'cdx-json'

export interface GenerateMetadata {
  applicationId: string
  componentName: string
  repositoryUrl: string
  sourceBranch: string
  outputFormat: string
}

export interface GenerateResponse {
  task_id: string
  status: string
  status_url: string
  estimated_seconds: number
}

// Submit a manifest straight into the SBOM pipeline (creates a job, returns 202).
export function generateSbom(file: File, meta: GenerateMetadata): Promise<GenerateResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('application_id', meta.applicationId)
  form.append('component_name', meta.componentName)
  form.append('repository_url', meta.repositoryUrl)
  form.append('source_branch', meta.sourceBranch)
  form.append('output_format', meta.outputFormat)
  return apiUpload<GenerateResponse>('/sbom/generate/', form)
}

// One analysis report's summary, as merged into SBOMJob.summary_stats at aggregate.
export interface ReportSummary {
  failed: boolean
  failure_reason: string | null
  [key: string]: unknown // report-specific counts (e.g. vulnerable_package_count, tier counts)
}

export interface SummaryStats {
  total_packages?: number
  reports?: Record<string, ReportSummary>
}

export interface JobStatus {
  task_id: string
  status: string // PENDING | PROGRESS | SUCCESS | FAILED
  progress: number
  current_phase: string
  failure_reason: string | null
  result_url: string | null
  output_format?: string
  summary_stats?: SummaryStats
  created_at: string
  completed_at: string | null
  artifacts_available: boolean // false once artifacts were cleaned (expiry/manual delete) (Story 7.3)
  artifacts_expire_at: string | null // when the artifacts are/were scheduled to expire
}

export const TERMINAL_STATUSES = ['SUCCESS', 'FAILED']

export function getJobStatus(taskId: string, apiKey?: string): Promise<JobStatus> {
  return apiRequest<JobStatus>(`/sbom/status/${taskId}/`, { apiKey })
}

// A row in the dashboard jobs list.
export interface JobListItem {
  task_id: string
  created_at: string
  manifest_filename: string
  manifest_format: string
  output_format: string
  status: string
  failure_reason: string | null
  elapsed_seconds: number | null // wall-clock time to complete; null while running (Story 6.3)
  artifacts_available: boolean // false once artifacts were cleaned (expiry/manual delete) (Story 7.3)
  artifacts_expire_at: string | null // when the artifacts are/were scheduled to expire
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface JobsQuery {
  page?: number
  status?: string // All | In Progress | Completed | Failed
  format?: string
}

export function listJobs(query: JobsQuery = {}): Promise<Paginated<JobListItem>> {
  const params = new URLSearchParams()
  if (query.page) params.set('page', String(query.page))
  if (query.status && query.status !== 'All') params.set('status', query.status)
  if (query.format) params.set('format', query.format)
  const qs = params.toString()
  return apiRequest<Paginated<JobListItem>>(`/sbom/jobs/${qs ? `?${qs}` : ''}`)
}

// Delete one job's artifacts on demand (Story 7.2). The job record is retained;
// only the SBOM + report blobs are removed. Idempotent.
export function deleteJobArtifacts(taskId: string): Promise<{ task_id: string; deleted: boolean }> {
  return apiRequest(`/sbom/jobs/${taskId}/artifacts/`, { method: 'DELETE' })
}

// Bulk-delete artifacts: a selected list of the org's jobs, or (admin) the whole org.
export function bulkDeleteArtifacts(opts: {
  taskIds?: string[]
  all?: boolean
}): Promise<{ deleted: number; requested?: number; scope?: string }> {
  const body = opts.all ? { all: true } : { task_ids: opts.taskIds ?? [] }
  return apiRequest('/sbom/jobs/artifacts/bulk-delete/', { method: 'POST', body })
}
