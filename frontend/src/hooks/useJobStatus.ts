// Shared job-status polling primitive (Story 6.2). The single sanctioned way to
// poll GET /sbom/status/{taskId}/ — no per-component polling loops (AD-5). Polls
// every 5s until the job reaches a terminal state, then stops. Reused by
// ResultsPage and each in-progress HistoryPage row.
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getJobStatus, TERMINAL_STATUSES, type JobStatus } from '../api/jobs'

export const POLL_MS = 5000

// Cross-org and unknown jobs both surface as 403/404 (no existence leak, AD-2).
export type JobStatusError = 'denied' | 'error' | null

export interface UseJobStatusResult {
  status: JobStatus | null
  error: JobStatusError
}

export interface UseJobStatusOptions {
  // When false, no requests are issued (e.g. a row already in a terminal state).
  enabled?: boolean
}

export function useJobStatus(
  taskId: string | undefined,
  { enabled = true }: UseJobStatusOptions = {},
): UseJobStatusResult {
  const [status, setStatus] = useState<JobStatus | null>(null)
  const [error, setError] = useState<JobStatusError>(null)

  useEffect(() => {
    if (!taskId || !enabled) return
    const id = taskId
    let active = true
    let timer = 0

    async function poll() {
      try {
        const next = await getJobStatus(id)
        if (!active) return
        setStatus(next)
        if (!TERMINAL_STATUSES.includes(next.status)) {
          timer = window.setTimeout(poll, POLL_MS)
        }
      } catch (err) {
        if (!active) return
        setError(err instanceof ApiError && (err.status === 403 || err.status === 404) ? 'denied' : 'error')
      }
    }

    void poll()
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [taskId, enabled])

  return { status, error }
}
