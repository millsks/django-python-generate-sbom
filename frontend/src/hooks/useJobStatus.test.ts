import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { ApiError } from '../api/client'
import { getJobStatus, type JobStatus } from '../api/jobs'
import { useJobStatus } from './useJobStatus'

vi.mock('../api/jobs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/jobs')>()
  return { ...actual, getJobStatus: vi.fn() }
})
const mockStatus = getJobStatus as Mock

function status(overrides: Partial<JobStatus> = {}): JobStatus {
  return {
    task_id: 't',
    status: 'PROGRESS',
    progress: 10,
    current_phase: 'resolving',
    failure_reason: null,
    result_url: null,
    created_at: '',
    completed_at: null,
    artifacts_available: true,
    artifacts_expire_at: null,
    ...overrides,
  }
}

// Flush the immediate first poll (not on a timer) plus any pending microtasks.
async function flush() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0)
  })
}

describe('useJobStatus', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
    mockStatus.mockReset()
  })

  it('issues no requests when disabled', async () => {
    mockStatus.mockResolvedValue(status())
    const { result } = renderHook(() => useJobStatus('t', { enabled: false }))
    await flush()

    expect(mockStatus).not.toHaveBeenCalled()
    expect(result.current.status).toBeNull()
  })

  it('polls every 5s while non-terminal, then stops on a terminal state', async () => {
    mockStatus
      .mockResolvedValueOnce(status({ progress: 10 }))
      .mockResolvedValueOnce(status({ progress: 50 }))
      .mockResolvedValueOnce(status({ status: 'SUCCESS', progress: 100 }))
    const { result } = renderHook(() => useJobStatus('t'))

    await flush()
    expect(mockStatus).toHaveBeenCalledTimes(1)
    expect(result.current.status?.progress).toBe(10)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(mockStatus).toHaveBeenCalledTimes(2)
    expect(result.current.status?.progress).toBe(50)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(mockStatus).toHaveBeenCalledTimes(3)
    expect(result.current.status?.status).toBe('SUCCESS')

    // Terminal → no further polling.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15000)
    })
    expect(mockStatus).toHaveBeenCalledTimes(3)
  })

  it('does not schedule another poll after a terminal first response', async () => {
    mockStatus.mockResolvedValue(status({ status: 'FAILED', failure_reason: 'boom' }))
    renderHook(() => useJobStatus('t'))

    await flush()
    expect(mockStatus).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(15000)
    })
    expect(mockStatus).toHaveBeenCalledTimes(1)
  })

  it('clears the timer on unmount', async () => {
    mockStatus.mockResolvedValue(status())
    const { unmount } = renderHook(() => useJobStatus('t'))

    await flush()
    expect(mockStatus).toHaveBeenCalledTimes(1)

    unmount()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15000)
    })
    expect(mockStatus).toHaveBeenCalledTimes(1)
  })

  it('maps a 403/404 to a denied error', async () => {
    mockStatus.mockRejectedValue(new ApiError('Job not found.', 404, 'not_found'))
    const { result } = renderHook(() => useJobStatus('t'))

    await flush()
    expect(result.current.error).toBe('denied')
  })
})
