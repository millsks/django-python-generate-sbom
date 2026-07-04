// Job-related API calls. Expanded in Epic 3 (submission) and Epic 6 (history).
import { apiRequest } from './client'

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
}

export const TERMINAL_STATUSES = ['SUCCESS', 'FAILED']

export function getJobStatus(taskId: string, apiKey?: string): Promise<JobStatus> {
  return apiRequest<JobStatus>(`/sbom/status/${taskId}/`, { apiKey })
}
