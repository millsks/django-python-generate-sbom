// Auth API calls: register, login, logout.
import { apiRequest } from './client'

export interface OrgSummary {
  slug: string
  name: string
}

export interface RegisterResponse {
  user: { id: number; email: string }
  org: OrgSummary
}

export function register(email: string, password: string): Promise<RegisterResponse> {
  return apiRequest<RegisterResponse>('/auth/register/', {
    method: 'POST',
    body: { email, password },
  })
}

export function login(email: string, password: string): Promise<{ org: OrgSummary | null }> {
  return apiRequest<{ org: OrgSummary | null }>('/auth/login/', {
    method: 'POST',
    body: { email, password },
  })
}

export function logout(): Promise<void> {
  return apiRequest<void>('/auth/logout/', { method: 'POST' })
}
