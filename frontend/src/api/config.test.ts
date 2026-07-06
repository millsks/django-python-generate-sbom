import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { apiRequest } from './client'
import { getAppConfig } from './config'

vi.mock('./client', () => ({ apiRequest: vi.fn() }))
const mockApiRequest = apiRequest as Mock

afterEach(() => {
  mockApiRequest.mockReset()
})

describe('getAppConfig', () => {
  it('GETs the public config endpoint and returns the flags', async () => {
    mockApiRequest.mockResolvedValue({ api_docs_enabled: true })

    await expect(getAppConfig()).resolves.toEqual({ api_docs_enabled: true })
    expect(mockApiRequest).toHaveBeenCalledWith('/config/')
  })
})
