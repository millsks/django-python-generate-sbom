import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { apiRequest } from './client'
import { addMember } from './orgs'

vi.mock('./client', () => ({ apiRequest: vi.fn() }))
const mockApiRequest = apiRequest as Mock

afterEach(() => {
  mockApiRequest.mockReset()
})

describe('addMember', () => {
  it('POSTs the email only (Story 2.7 — no temp password)', async () => {
    mockApiRequest.mockResolvedValue({ user_id: 2, email: 'bob@example.com', role: 'member', joined_at: '' })

    await addMember('bob@example.com')

    expect(mockApiRequest).toHaveBeenCalledWith('/orgs/members/', {
      method: 'POST',
      body: { email: 'bob@example.com' },
    })
  })
})
