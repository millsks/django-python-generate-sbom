// Job-related API calls. Expanded in Epic 3 (submission) and Epic 6 (history).
import { apiRequest } from './client'

export interface JobStatus {
  task_id: string
  status: string
  progress: number
  current_step: string
}

export function getJobStatus(taskId: string, apiKey?: string): Promise<JobStatus> {
  return apiRequest<JobStatus>(`/sbom/status/${taskId}/`, { apiKey })
}
