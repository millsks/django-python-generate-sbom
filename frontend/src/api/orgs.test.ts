import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { apiRequest } from './client'
import { addMember, demoteAdmin, grantGlobalAdmin, listGlobalAdmins, promoteAdmin, revokeGlobalAdmin } from './orgs'

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

describe('promoteAdmin', () => {
  it('POSTs the user_id to promote-admin (Story 2.16)', async () => {
    mockApiRequest.mockResolvedValue(undefined)

    await promoteAdmin(2)

    expect(mockApiRequest).toHaveBeenCalledWith('/orgs/promote-admin/', {
      method: 'POST',
      body: { user_id: 2 },
    })
  })
})

describe('demoteAdmin', () => {
  it('POSTs the user_id to demote-admin (Story 2.20)', async () => {
    mockApiRequest.mockResolvedValue(undefined)

    await demoteAdmin(2)

    expect(mockApiRequest).toHaveBeenCalledWith('/orgs/demote-admin/', {
      method: 'POST',
      body: { user_id: 2 },
    })
  })
})

describe('global-admin management (Story 13.1)', () => {
  it('listGlobalAdmins GETs the endpoint', async () => {
    mockApiRequest.mockResolvedValue({ global_admins: [] })
    await listGlobalAdmins()
    expect(mockApiRequest).toHaveBeenCalledWith('/admin/global-admins/')
  })

  it('grantGlobalAdmin POSTs the email', async () => {
    mockApiRequest.mockResolvedValue({ user_id: 3, email: 'bob@example.com' })
    await grantGlobalAdmin('bob@example.com')
    expect(mockApiRequest).toHaveBeenCalledWith('/admin/global-admins/', {
      method: 'POST',
      body: { email: 'bob@example.com' },
    })
  })

  it('revokeGlobalAdmin DELETEs the user', async () => {
    mockApiRequest.mockResolvedValue(undefined)
    await revokeGlobalAdmin(3)
    expect(mockApiRequest).toHaveBeenCalledWith('/admin/global-admins/3/', { method: 'DELETE' })
  })
})
