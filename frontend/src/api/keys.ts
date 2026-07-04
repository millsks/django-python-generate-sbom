// API-key management calls (create, list, revoke).
import { apiRequest } from './client'

export interface ApiKey {
  id: string
  name: string
  prefix: string
  created_at: string
  last_used_at: string | null
}

export interface CreatedKey {
  id: string
  name: string
  prefix: string
  key: string
}

export function getKeys(): Promise<ApiKey[]> {
  return apiRequest<ApiKey[]>('/keys/')
}

export function createKey(name: string): Promise<CreatedKey> {
  return apiRequest<CreatedKey>('/keys/', { method: 'POST', body: { name } })
}

export function revokeKey(id: string): Promise<void> {
  return apiRequest<void>(`/keys/${id}/`, { method: 'DELETE' })
}
