// Job-related API calls. Expanded in Epic 3 (submission) and Epic 6 (history).
import { apiRequest } from './client'

export interface JobStatus {
  task_id: string
  status: string // PENDING | PROGRESS | SUCCESS | FAILED
  progress: number
  current_phase: string
  failure_reason: string | null
  result_url: string | null
  created_at: string
  completed_at: string | null
}

export const TERMINAL_STATUSES = ['SUCCESS', 'FAILED']

export function getJobStatus(taskId: string, apiKey?: string): Promise<JobStatus> {
  return apiRequest<JobStatus>(`/sbom/status/${taskId}/`, { apiKey })
}
